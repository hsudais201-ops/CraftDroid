#!/usr/bin/env python3
from pathlib import Path
import sys

WORLD_MANAGER = r'''package com.example.launcher

import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.channels.FileChannel
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardCopyOption
import java.time.Instant
import java.time.format.DateTimeFormatter
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

/**
 * Step 177 core world/save manager.
 *
 * Worlds are kept inside an instance's saves directory. Mutating operations
 * refuse to touch a world while Minecraft holds its session.lock file.
 * Backups/imports are written to temporary files and atomically moved into
 * place where the filesystem supports it.
 */
class WorldManager(private val instanceRoot: File) {
    private val savesDir = File(instanceRoot, "saves")
    private val backupsDir = File(instanceRoot, "backups/worlds")
    private val timestampFormat = DateTimeFormatter.ISO_INSTANT

    data class WorldInfo(
        val name: String,
        val directory: File,
        val sizeBytes: Long,
        val lastModified: Long,
        val hasLevelData: Boolean
    )

    data class BackupInfo(
        val worldName: String,
        val file: File,
        val createdAt: Long,
        val sizeBytes: Long
    )

    fun listWorlds(): List<WorldInfo> {
        if (!savesDir.isDirectory) return emptyList()
        return savesDir.listFiles()
            ?.filter { it.isDirectory && !it.isSymbolicLink() }
            ?.map { world ->
                WorldInfo(
                    name = world.name,
                    directory = world,
                    sizeBytes = directorySize(world),
                    lastModified = world.lastModified(),
                    hasLevelData = File(world, "level.dat").isFile
                )
            }
            ?.sortedWith(compareByDescending<WorldInfo> { it.lastModified }.thenBy { it.name.lowercase() })
            ?: emptyList()
    }

    fun listBackups(worldName: String): List<BackupInfo> {
        val safeName = safeName(worldName)
        val dir = File(backupsDir, safeName)
        return dir.listFiles { file -> file.isFile && file.extension == "zip" }
            ?.map { file -> BackupInfo(safeName, file, file.lastModified(), file.length()) }
            ?.sortedByDescending { it.createdAt }
            ?: emptyList()
    }

    fun backupWorld(worldName: String): BackupInfo {
        val world = requireWorld(worldName)
        withWorldUnlocked(world) {
            val destinationDir = File(backupsDir, safeName(worldName)).apply { mkdirs() }
            check(destinationDir.isDirectory) { "Unable to create world backup directory" }
            val stamp = timestampFormat.format(Instant.now()).replace(":", "-")
            val finalFile = File(destinationDir, "${safeName(worldName)}-$stamp.zip")
            val tempFile = File(destinationDir, ".${finalFile.name}.tmp")
            if (tempFile.exists()) tempFile.delete()
            zipDirectory(world.toPath(), tempFile.toPath())
            moveAtomically(tempFile.toPath(), finalFile.toPath())
            return BackupInfo(safeName(worldName), finalFile, finalFile.lastModified(), finalFile.length())
        }
    }

    fun restoreBackup(worldName: String, backup: File): WorldInfo {
        val world = requireWorld(worldName)
        require(backup.isFile && backup.extension == "zip") { "Invalid world backup" }
        require(backup.canonicalFile.startsWith(backupsDir.canonicalFile)) { "Backup is outside the backup directory" }
        withWorldUnlocked(world) {
            val restoreTemp = File(savesDir, ".${safeName(worldName)}-restore-${System.nanoTime()}")
            restoreTemp.mkdirs()
            try {
                unzipSafely(backup.toPath(), restoreTemp.toPath())
                val extractedRoot = locateWorldRoot(restoreTemp.toPath())
                val stage = File(savesDir, ".${safeName(worldName)}-stage-${System.nanoTime()}")
                extractedRoot.toFile().copyRecursively(stage, overwrite = true)
                world.deleteRecursively()
                check(stage.renameTo(world)) { "Unable to install restored world" }
            } finally {
                restoreTemp.deleteRecursively()
            }
        }
        return worldInfo(world)
    }

    fun renameWorld(worldName: String, newName: String): WorldInfo {
        val world = requireWorld(worldName)
        val safeNewName = safeName(newName)
        val target = File(savesDir, safeNewName)
        require(!target.exists()) { "A world named '$safeNewName' already exists" }
        withWorldUnlocked(world) {
            check(world.renameTo(target)) { "Unable to rename world" }
        }
        return worldInfo(target)
    }

    fun deleteWorld(worldName: String) {
        val world = requireWorld(worldName)
        withWorldUnlocked(world) {
            check(world.deleteRecursively()) { "Unable to delete world" }
        }
    }

    fun importWorld(archive: File, requestedName: String? = null): WorldInfo {
        require(archive.isFile && archive.extension.lowercase() == "zip") { "World archive must be a ZIP file" }
        savesDir.mkdirs()
        val targetName = safeName(requestedName ?: archive.nameWithoutExtension)
        val target = File(savesDir, targetName)
        require(!target.exists()) { "A world named '$targetName' already exists" }
        val stage = File(savesDir, ".import-${System.nanoTime()}")
        stage.mkdirs()
        try {
            unzipSafely(archive.toPath(), stage.toPath())
            val root = locateWorldRoot(stage.toPath()).toFile()
            check(File(root, "level.dat").isFile) { "Archive does not contain a valid Minecraft world" }
            check(root.renameTo(target)) { "Unable to install imported world" }
        } finally {
            stage.deleteRecursively()
        }
        return worldInfo(target)
    }

    fun exportWorld(worldName: String, destination: File): File {
        val world = requireWorld(worldName)
        withWorldUnlocked(world) {
            val parent = destination.parentFile ?: throw IllegalArgumentException("Destination has no parent")
            parent.mkdirs()
            val temp = File(parent, ".${destination.name}.tmp")
            if (temp.exists()) temp.delete()
            zipDirectory(world.toPath(), temp.toPath())
            moveAtomically(temp.toPath(), destination.toPath())
        }
        return destination
    }

    private fun requireWorld(name: String): File {
        val safe = safeName(name)
        val world = File(savesDir, safe)
        require(world.isDirectory && !world.isSymbolicLink()) { "World '$safe' was not found" }
        return world
    }

    private fun safeName(value: String): String {
        val trimmed = value.trim()
        require(trimmed.isNotEmpty() && trimmed != "." && trimmed != "..") { "World name is empty" }
        require(trimmed.length <= 128) { "World name is too long" }
        require(trimmed.none { it == '/' || it == '\\' || it == '\u0000' }) { "World name contains an invalid path character" }
        return trimmed
    }

    private fun withWorldUnlocked(world: File, action: () -> Unit) {
        val lockFile = File(world, "session.lock")
        if (!lockFile.exists()) {
            action()
            return
        }
        FileInputStream(lockFile).channel.use { channel ->
            try {
                channel.tryLock()?.use {
                    action()
                } ?: throw WorldLockedException(world.name)
            } catch (_: java.nio.channels.OverlappingFileLockException) {
                throw WorldLockedException(world.name)
            }
        }
    }

    private fun worldInfo(world: File) = WorldInfo(
        name = world.name,
        directory = world,
        sizeBytes = directorySize(world),
        lastModified = world.lastModified(),
        hasLevelData = File(world, "level.dat").isFile
    )

    private fun directorySize(root: File): Long {
        if (root.isFile) return root.length()
        return root.walkTopDown().filter { it.isFile && !it.isSymbolicLink() }.sumOf { it.length() }
    }

    private fun zipDirectory(source: Path, destination: Path) {
        ZipOutputStream(BufferedOutputStream(FileOutputStream(destination.toFile()))).use { zip ->
            Files.walk(source).use { stream ->
                stream.filter { Files.isRegularFile(it) && !Files.isSymbolicLink(it) }.forEach { file ->
                    val relative = source.relativize(file).toString().replace(File.separatorChar, '/')
                    zip.putNextEntry(ZipEntry(relative))
                    BufferedInputStream(FileInputStream(file.toFile())).use { input -> input.copyTo(zip) }
                    zip.closeEntry()
                }
            }
        }
    }

    private fun unzipSafely(zip: Path, destination: Path) {
        val root = destination.toFile().canonicalFile
        ZipInputStream(BufferedInputStream(FileInputStream(zip.toFile()))).use { input ->
            var entry = input.nextEntry
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (entry != null) {
                val output = File(root, entry.name).canonicalFile
                require(output.toPath().startsWith(root.toPath())) { "Unsafe archive entry: ${entry.name}" }
                if (entry.isDirectory) {
                    output.mkdirs()
                } else {
                    output.parentFile?.mkdirs()
                    FileOutputStream(output).use { out ->
                        var read = input.read(buffer)
                        while (read >= 0) {
                            if (read > 0) out.write(buffer, 0, read)
                            read = input.read(buffer)
                        }
                    }
                }
                input.closeEntry()
                entry = input.nextEntry
            }
        }
    }

    private fun locateWorldRoot(stage: Path): Path {
        if (Files.isRegularFile(stage.resolve("level.dat"))) return stage
        val children = stage.toFile().listFiles().orEmpty().filter { it.isDirectory && !it.isSymbolicLink() }
        require(children.size == 1) { "Archive must contain one world root" }
        val candidate = children.single().toPath()
        require(Files.isRegularFile(candidate.resolve("level.dat"))) { "No level.dat found in archive" }
        return candidate
    }

    private fun moveAtomically(from: Path, to: Path) {
        try {
            Files.move(from, to, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } catch (_: Exception) {
            Files.move(from, to, StandardCopyOption.REPLACE_EXISTING)
        }
    }

    companion object {
        private const val DEFAULT_BUFFER_SIZE = 32 * 1024
    }
}

class WorldLockedException(worldName: String) : IllegalStateException("World '$worldName' is currently in use")
'''

TEST = r'''package com.example.launcher

import java.io.File
import java.nio.file.Files
import java.util.zip.ZipFile
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertTrue

class WorldManagerStep177Test {
    @Test
    fun listsBacksUpExportsAndDeletesWorldSafely() {
        val root = Files.createTempDirectory("craftdroid-world-test").toFile()
        try {
            val world = File(root, "saves/TestWorld").apply { mkdirs() }
            File(world, "level.dat").writeBytes(byteArrayOf(1, 2, 3))
            File(world, "region").mkdirs()
            File(world, "region/r.0.0.mca").writeText("fixture")
            val manager = WorldManager(root)

            assertEquals(listOf("TestWorld"), manager.listWorlds().map { it.name })
            val backup = manager.backupWorld("TestWorld")
            assertTrue(backup.file.isFile)
            ZipFile(backup.file).use { zip -> assertTrue(zip.getEntry("level.dat") != null) }

            val exported = File(root, "exports/TestWorld.zip")
            manager.exportWorld("TestWorld", exported)
            assertTrue(exported.isFile)
            manager.deleteWorld("TestWorld")
            assertTrue(!world.exists())

            manager.importWorld(exported, "Restored")
            assertTrue(File(root, "saves/Restored/level.dat").isFile)
        } finally {
            root.deleteRecursively()
        }
    }

    @Test
    fun rejectsUnsafeArchiveEntries() {
        val root = Files.createTempDirectory("craftdroid-world-unsafe").toFile()
        try {
            val archive = File(root, "evil.zip")
            java.util.zip.ZipOutputStream(archive.outputStream()).use { zip ->
                zip.putNextEntry(java.util.zip.ZipEntry("../../escape.txt"))
                zip.write(1)
                zip.closeEntry()
            }
            assertFailsWith<IllegalArgumentException> { WorldManager(root).importWorld(archive, "Evil") }
        } finally {
            root.deleteRecursively()
        }
    }
}
'''


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if not matches:
        raise SystemExit(f"Could not find {name} under {root}")
    return matches[0]


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    java_root = root / "app" / "src" / "main" / "java"
    test_root = root / "app" / "src" / "test" / "java"
    if not java_root.is_dir():
        raise SystemExit(f"Android Java source root not found: {java_root}")
    package_dir = java_root / "com" / "example" / "launcher"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "WorldManager.kt").write_text(WORLD_MANAGER, encoding="utf-8")
    test_package = test_root / "com" / "example" / "launcher"
    test_package.mkdir(parents=True, exist_ok=True)
    (test_package / "WorldManagerStep177Test.kt").write_text(TEST, encoding="utf-8")
    print(f"Step 177 world manager installed at {package_dir / 'WorldManager.kt'}")
    print(f"Step 177 unit test installed at {test_package / 'WorldManagerStep177Test.kt'}")


if __name__ == "__main__":
    main()
