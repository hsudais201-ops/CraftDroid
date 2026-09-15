package com.example.launcher

import android.content.Context
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream

/**
 * Unified content library for worlds, mods, resource packs, shaders and modpacks.
 * All imports are performed inside the app-private Minecraft root and reject
 * absolute/path-traversal ZIP entries.
 */
object MinecraftContentManager {
    enum class Kind { MODPACK, MOD, SHADER, RESOURCE_PACK, WORLD }

    fun directory(context: Context, kind: Kind): File = when (kind) {
        Kind.MODPACK -> File(root(context), "modpacks")
        Kind.MOD -> File(root(context), "mods")
        Kind.SHADER -> File(root(context), "shaderpacks")
        Kind.RESOURCE_PACK -> File(root(context), "resourcepacks")
        Kind.WORLD -> File(root(context), "saves")
    }

    fun ensureDirectories(context: Context) {
        Kind.values().forEach { directory(context, it).mkdirs() }
        File(root(context), "versions").mkdirs()
        File(root(context), "config").mkdirs()
    }

    fun list(context: Context, kind: Kind): List<File> = directory(context, kind)
        .listFiles()
        ?.filter { it.isFile || it.isDirectory }
        ?.sortedBy { it.name.lowercase() }
        ?: emptyList()

    /** Import a file by copying it into the appropriate library directory. */
    fun importFile(context: Context, kind: Kind, source: File, desiredName: String? = null): File {
        require(source.isFile && source.length() > 0L) { "Source file is empty or missing" }
        ensureDirectories(context)
        val safeName = sanitizeFileName(desiredName ?: source.name)
        val destination = File(directory(context, kind), safeName).canonicalFile
        require(destination.parentFile?.canonicalFile == directory(context, kind).canonicalFile) {
            "Unsafe content destination"
        }
        copy(source, destination)
        return destination
    }

    /** Import a ZIP/JAR modpack or world archive with traversal protection. */
    fun importArchive(context: Context, kind: Kind, archive: File): File {
        require(archive.isFile && archive.length() > 0L) { "Archive is empty or missing" }
        ensureDirectories(context)
        val targetRoot = File(directory(context, kind), sanitizeFileName(archive.nameWithoutExtension)).canonicalFile
        if (!targetRoot.exists() && !targetRoot.mkdirs()) throw IOException("Could not create $targetRoot")

        ZipInputStream(BufferedInputStream(FileInputStream(archive))).use { zis ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val entry = zis.nextEntry ?: break
                val entryName = entry.name.replace('\\', '/')
                if (entryName.startsWith("/") || entryName.contains("../") || entryName.contains("..\\") ||
                    entryName.matches(Regex("^[A-Za-z]:/.*"))) {
                    throw IOException("Unsafe ZIP entry: $entryName")
                }
                val out = File(targetRoot, entryName).canonicalFile
                require(out.path == targetRoot.path || out.path.startsWith(targetRoot.path + File.separator)) {
                    "ZIP entry escapes target directory"
                }
                if (entry.isDirectory) {
                    if (!out.exists() && !out.mkdirs()) throw IOException("Could not create $out")
                } else {
                    out.parentFile?.mkdirs()
                    FileOutputStream(out, false).use { output ->
                        while (true) {
                            val n = zis.read(buffer)
                            if (n < 0) break
                            output.write(buffer, 0, n)
                        }
                        output.fd.sync()
                    }
                }
            }
        }
        return targetRoot
    }

    fun remove(context: Context, kind: Kind, file: File): Boolean {
        val base = directory(context, kind).canonicalFile
        val candidate = file.canonicalFile
        require(candidate.parentFile?.canonicalFile == base || candidate.path.startsWith(base.path + File.separator)) {
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
        destination.parentFile?.mkdirs()
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
        if (file.isDirectory) file.listFiles()?.forEach { deleteRecursively(it) }
        return !file.exists() || file.delete()
    }
}
