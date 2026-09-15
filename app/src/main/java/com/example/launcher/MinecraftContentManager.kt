package com.example.launcher

import android.content.Context
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipInputStream

/**
 * Unified content library for worlds, mods, resource packs, shaders and modpacks.
 * All imports stay inside the app-private Minecraft root and reject traversal,
 * oversized entries, archive bombs, and source/destination self-overwrites.
 */
object MinecraftContentManager {
    enum class Kind { MODPACK, MOD, SHADER, RESOURCE_PACK, WORLD }

    private const val MAX_ARCHIVE_BYTES = 1L * 1024L * 1024L * 1024L
    private const val MAX_ENTRY_BYTES = 256L * 1024L * 1024L
    private const val MAX_ENTRIES = 10_000

    fun directory(context: Context, kind: Kind): File = when (kind) {
        Kind.MODPACK -> File(root(context), "modpacks")
        Kind.MOD -> File(root(context), "mods")
        Kind.SHADER -> File(root(context), "shaderpacks")
        Kind.RESOURCE_PACK -> File(root(context), "resourcepacks")
        Kind.WORLD -> File(root(context), "saves")
    }

    fun ensureDirectories(context: Context) {
        Kind.values().forEach {
            val dir = directory(context, it)
            if (!dir.exists() && !dir.mkdirs() && !dir.isDirectory) {
                throw IOException("Could not create content directory $dir")
            }
        }
        listOf("versions", "config").forEach { name ->
            val dir = File(root(context), name)
            if (!dir.exists() && !dir.mkdirs() && !dir.isDirectory) {
                throw IOException("Could not create Minecraft directory $dir")
            }
        }
    }

    fun list(context: Context, kind: Kind): List<File> = directory(context, kind)
        .listFiles()
        ?.filter { it.isFile || it.isDirectory }
        ?.sortedBy { it.name.lowercase() }
        ?: emptyList()

    /** Import a file by copying it into the appropriate library directory. */
    fun importFile(context: Context, kind: Kind, source: File, desiredName: String? = null): File {
        require(source.isFile && source.length() > 0L) { "Source file is empty or missing" }
        require(source.length() <= MAX_ARCHIVE_BYTES) { "Source file exceeds safety limit" }
        ensureDirectories(context)
        val base = directory(context, kind).canonicalFile
        val safeName = sanitizeFileName(desiredName ?: source.name)
        val destination = File(base, safeName).canonicalFile
        require(destination.parentFile?.canonicalFile == base) { "Unsafe content destination" }
        if (source.canonicalFile == destination) return destination
        copy(source, destination)
        return destination
    }

    /** Import a ZIP/JAR modpack or world archive with traversal and size protection. */
    fun importArchive(context: Context, kind: Kind, archive: File): File {
        require(archive.isFile && archive.length() > 0L) { "Archive is empty or missing" }
        require(archive.length() <= MAX_ARCHIVE_BYTES) { "Archive exceeds safety limit" }
        ensureDirectories(context)
        val base = directory(context, kind).canonicalFile
        val targetRoot = File(base, sanitizeFileName(archive.nameWithoutExtension)).canonicalFile
        require(targetRoot.parentFile?.canonicalFile == base) { "Unsafe archive destination" }
        val staging = File(base, ".${targetRoot.name}.importing-${System.nanoTime()}").canonicalFile
        require(staging.parentFile?.canonicalFile == base) { "Unsafe staging destination" }
        if (!staging.mkdirs()) throw IOException("Could not create staging directory $staging")

        try {
            ZipInputStream(BufferedInputStream(FileInputStream(archive))).use { zis ->
                val buffer = ByteArray(64 * 1024)
                var entryCount = 0
                var totalBytes = 0L
                while (true) {
                    val entry = zis.nextEntry ?: break
                    if (++entryCount > MAX_ENTRIES) throw IOException("Archive contains too many entries")
                    val entryName = entry.name.replace('\\', '/')
                    if (entryName.startsWith("/") || entryName.contains("../") ||
                        entryName.matches(Regex("^[A-Za-z]:/.*"))) {
                        throw IOException("Unsafe ZIP entry: $entryName")
                    }
                    val out = File(staging, entryName).canonicalFile
                    require(out.path == staging.path || out.path.startsWith(staging.path + File.separator)) {
                        "ZIP entry escapes target directory"
                    }
                    if (entry.isDirectory) {
                        if (!out.exists() && !out.mkdirs()) throw IOException("Could not create $out")
                        continue
                    }

                    out.parentFile?.let { parent ->
                        if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                            throw IOException("Could not create $parent")
                        }
                    }
                    var entryBytes = 0L
                    FileOutputStream(out, false).use { output ->
                        while (true) {
                            val n = zis.read(buffer)
                            if (n < 0) break
                            entryBytes += n
                            totalBytes += n
                            if (entryBytes > MAX_ENTRY_BYTES) throw IOException("ZIP entry exceeds safety limit")
                            if (totalBytes > MAX_ARCHIVE_BYTES) throw IOException("Expanded archive exceeds safety limit")
                            output.write(buffer, 0, n)
                        }
                        output.fd.sync()
                    }
                }
            }

            if (targetRoot.exists() && !deleteRecursively(targetRoot)) {
                throw IOException("Could not replace existing imported content $targetRoot")
            }
            if (!staging.renameTo(targetRoot)) {
                throw IOException("Could not finalize imported content $targetRoot")
            }
            return targetRoot
        } catch (t: Throwable) {
            deleteRecursively(staging)
            throw t
        }
    }

    fun remove(context: Context, kind: Kind, file: File): Boolean {
        val base = directory(context, kind).canonicalFile
        val candidate = file.canonicalFile
        require(candidate != base && candidate.path.startsWith(base.path + File.separator)) {
            "Refusing to delete outside Minecraft content directory"
        }
        return deleteRecursively(candidate)
    }

    private fun root(context: Context): File = File(context.filesDir, "minecraft")

    private fun sanitizeFileName(raw: String): String {
        val cleaned = raw.replace(Regex("[\\\\/:*?\"<>|]"), "_").trim()
        require(cleaned.isNotBlank() && cleaned != "." && cleaned != "..") { "Invalid content name" }
        return cleaned.take(180)
    }

    private fun copy(source: File, destination: File) {
        destination.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                throw IOException("Could not create destination directory $parent")
            }
        }
        FileInputStream(source).use { input ->
            FileOutputStream(destination, false).use { output ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val n = input.read(buffer)
                    if (n < 0) break
                    output.write(buffer, 0, n)
                }
                output.fd.sync()
            }
        }
    }

    private fun deleteRecursively(file: File): Boolean {
        if (file.isDirectory) file.listFiles()?.forEach { child ->
            if (!deleteRecursively(child)) return false
        }
        return !file.exists() || file.delete()
    }
}
