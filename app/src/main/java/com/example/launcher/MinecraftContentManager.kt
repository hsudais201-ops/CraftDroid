package com.example.launcher

import android.content.Context
import com.example.filesystem.MinecraftFileSystem
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipFile

object MinecraftContentManager {
    enum class Kind { MOD, MODPACK, SHADER, RESOURCE_PACK, WORLD }

    fun list(context: Context, kind: Kind): List<File> {
        val fs = MinecraftFileSystem(context)
        val dir = when (kind) {
            Kind.MOD -> fs.modsDir
            Kind.MODPACK -> File(fs.rootDir, "modpacks").apply { mkdirs() }
            Kind.SHADER -> fs.shaderPacksDir
            Kind.RESOURCE_PACK -> fs.resourcePacksDir
            Kind.WORLD -> fs.savesDir
        }
        return dir.listFiles()?.filter { it.exists() }?.sortedBy { it.name.lowercase() }.orEmpty()
    }

    fun importFile(context: Context, kind: Kind, source: File, originalName: String): File {
        val fs = MinecraftFileSystem(context)
        val destinationDir = when (kind) {
            Kind.MOD -> fs.modsDir
            Kind.SHADER -> fs.shaderPacksDir
            Kind.RESOURCE_PACK -> fs.resourcePacksDir
            Kind.MODPACK -> File(fs.rootDir, "modpacks").apply { mkdirs() }
            Kind.WORLD -> fs.savesDir
        }.apply { mkdirs() }
        val safeName = originalName.substringAfterLast('/').substringAfterLast('\\').ifBlank { source.name }
        val destination = File(destinationDir, safeName)
        source.copyTo(destination, overwrite = true)
        return destination
    }

    fun importArchive(context: Context, kind: Kind, archive: File): File {
        val fs = MinecraftFileSystem(context)
        return when (kind) {
            Kind.WORLD -> {
                val base = fs.savesDir
                ZipFile(archive).use { zip ->
                    val root = zip.entries().asSequence().map { it.name.substringBefore('/') }.firstOrNull().orEmpty()
                    val worldName = root.ifBlank { archive.nameWithoutExtension }
                    val target = safeDirectory(base, worldName)
                    extractZip(zip, target)
                    target
                }
            }
            else -> importFile(context, kind, archive, archive.name)
        }
    }

    private fun safeDirectory(parent: File, name: String): File {
        val safe = name.replace(Regex("[^A-Za-z0-9._ -]"), "_").trim().ifBlank { "world" }
        return File(parent, safe).apply { mkdirs() }
    }

    private fun extractZip(zip: ZipFile, destination: File) {
        val base = destination.canonicalFile
        val entries = zip.entries()
        while (entries.hasMoreElements()) {
            val entry = entries.nextElement()
            val target = File(destination, entry.name).canonicalFile
            require(target.path == base.path || target.path.startsWith(base.path + File.separator)) {
                "Unsafe archive entry: ${entry.name}"
            }
            if (entry.isDirectory) {
                target.mkdirs()
            } else {
                target.parentFile?.mkdirs()
                zip.getInputStream(entry).use { input ->
                    FileOutputStream(target).use { output -> input.copyTo(output) }
                }
            }
        }
    }
}

data class ModpackInstallResult(val instanceDirectory: File)

object MinecraftModpackManager {
    suspend fun install(context: Context, archive: File): ModpackInstallResult {
        val fs = MinecraftFileSystem(context)
        val modpacksDir = File(fs.rootDir, "modpacks").apply { mkdirs() }
        val index = org.json.JSONObject(
            ZipFile(archive).use { zip ->
                val entry = zip.getEntry("modrinth.index.json") ?: error("Not a Modrinth .mrpack archive")
                zip.getInputStream(entry).bufferedReader().use { it.readText() }
            }
        )
        val name = index.optString("name").ifBlank { archive.nameWithoutExtension }
            .replace(Regex("[^A-Za-z0-9._ -]"), "_")
        val instance = File(modpacksDir, name).apply { mkdirs() }
        val base = instance.canonicalFile

        // 1) Extract overrides exactly as the mrpack contract specifies.
        ZipFile(archive).use { zip ->
            val overrides = zip.entries().asSequence().filter { it.name.startsWith("overrides/") }
            overrides.forEach { entry ->
                val relative = entry.name.removePrefix("overrides/")
                if (relative.isBlank()) return@forEach
                val target = File(instance, relative).canonicalFile
                require(target.path == base.path || target.path.startsWith(base.path + File.separator)) {
                    "Unsafe modpack override entry: " + entry.name
                }
                if (entry.isDirectory) target.mkdirs() else {
                    target.parentFile?.mkdirs()
                    zip.getInputStream(entry).use { input ->
                        FileOutputStream(target).use { output -> input.copyTo(output) }
                    }
                }
            }
        }

        // 2) Download every file listed by index.json. This is separate from
        // overrides and is required for a real .mrpack installation.
        val files = index.optJSONArray("files") ?: org.json.JSONArray()
        for (i in 0 until files.length()) {
            val entry = files.optJSONObject(i) ?: continue
            val path = entry.optString("path").replace('\\', '/')
            if (path.isBlank() || path.split('/').any { it == ".." } || path.startsWith("/")) {
                throw SecurityException("Blocked unsafe mrpack path: " + path)
            }
            val env = entry.optJSONObject("env")
            if (env?.optString("client") == "unsupported") continue

            val target = File(instance, path).canonicalFile
            require(target.path == base.path || target.path.startsWith(base.path + File.separator)) {
                "Unsafe modpack file path: " + path
            }
            target.parentFile?.mkdirs()

            val hashes = entry.optJSONObject("hashes")
            val sha1 = hashes?.optString("sha1").orEmpty()
            val downloads = entry.optJSONArray("downloads") ?: org.json.JSONArray()
            if (downloads.length() == 0) {
                // A few packs embed a file in overrides instead of providing a
                // remote download. Leave an existing override untouched.
                if (!target.isFile) throw java.io.IOException("No download URL for mrpack file: " + path)
                continue
            }
            val url = downloads.optString(0)
            require(url.startsWith("https://")) { "Untrusted mrpack download URL: " + url }

            val tmp = File(target.parentFile, target.name + ".part")
            downloadToFile(url, tmp, entry.optLong("fileSize", -1), sha1)
            if (tmp.renameTo(target) || tmp.copyTo(target, overwrite = true).exists()) tmp.delete()
        }

        File(instance, "manifest.json").writeText(index.toString(2))
        archive.copyTo(File(instance, "pack.mrpack"), overwrite = true)
        return ModpackInstallResult(instance)
    }

    private fun downloadToFile(url: String, target: File, expectedSize: Long, expectedSha1: String) {
        val connection = URL(url).openConnection().apply {
            connectTimeout = 15_000
            readTimeout = 45_000
        }
        val digest = MessageDigest.getInstance("SHA-1")
        var count = 0L
        connection.getInputStream().use { input ->
            target.parentFile?.mkdirs()
            FileOutputStream(target).use { output ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    output.write(buffer, 0, read)
                    digest.update(buffer, 0, read)
                    count += read
                }
                output.fd.sync()
            }
        }
        require(expectedSize <= 0L || count == expectedSize) {
            "Modpack file size verification failed: " + target.name
        }
        if (expectedSha1.isNotBlank()) {
            val actual = digest.digest().joinToString("") { "%02x".format(it) }
            require(actual.equals(expectedSha1, ignoreCase = true)) {
                "Modpack file hash verification failed: " + target.name
            }
        }
    }
}

