package com.example.launcher

import android.content.Context
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/**
 * Modrinth .mrpack installer.
 * Implements the published modpack layout: modrinth.index.json, downloaded
 * files, and overrides. Download hosts are restricted to the hosts permitted
 * by the Modrinth format specification, and every redirect is revalidated.
 */
object MinecraftModpackManager {
    data class Result(
        val name: String,
        val minecraftVersion: String?,
        val loader: MinecraftLoaderProfile.Loader,
        val instanceDirectory: File,
        val downloadedFiles: Int
    )

    private const val MAX_TOTAL_BYTES = 1024L * 1024L * 1024L
    private const val MAX_FILE_BYTES = 256L * 1024L * 1024L
    private const val MAX_ARCHIVE_ENTRIES = 10_000
    private const val CONNECT_TIMEOUT = 20_000
    private const val READ_TIMEOUT = 60_000
    private const val MAX_REDIRECTS = 3

    private val allowedHosts = setOf(
        "cdn.modrinth.com",
        "github.com",
        "raw.githubusercontent.com",
        "gitlab.com"
    )

    fun install(context: Context, mrpack: File): Result {
        require(mrpack.isFile && mrpack.length() > 0L) { "Modpack is empty or missing" }
        MinecraftContentManager.ensureDirectories(context)
        val staging = File(context.cacheDir, "mrpack-staging-${System.nanoTime()}").canonicalFile
        if (!staging.mkdirs()) throw IOException("Could not create modpack staging directory")
        try {
            unzip(mrpack, staging)
            val indexFile = File(staging, "modrinth.index.json")
            require(indexFile.isFile) { "Not a valid Modrinth modpack: modrinth.index.json is missing" }
            val index = JSONObject(indexFile.readText(Charsets.UTF_8))
            require(index.optString("game") == "minecraft") { "Modpack is not for Minecraft" }
            val formatVersion = index.optInt("formatVersion", 0)
            require(formatVersion == 1) { "Unsupported Modrinth modpack format: $formatVersion" }

            val name = sanitize(index.optString("name").ifBlank { mrpack.nameWithoutExtension })
            val base = MinecraftContentManager.directory(context, MinecraftContentManager.Kind.MODPACK).canonicalFile
            val target = File(base, name).canonicalFile
            require(target.parentFile?.canonicalFile == base) { "Unsafe modpack destination" }
            val importRoot = File(base, ".${name}.importing-${System.nanoTime()}").canonicalFile
            require(importRoot.parentFile?.canonicalFile == base) { "Unsafe modpack staging destination" }
            if (!importRoot.mkdirs()) throw IOException("Could not create modpack instance staging directory")

            val dependencies = index.optJSONObject("dependencies")
            val minecraft = dependencies?.optString("minecraft")?.takeIf { it.isNotBlank() }
            val loader = detectLoader(dependencies)
            var downloaded = 0
            try {
                val files = index.optJSONArray("files")
                var total = 0L
                if (files != null) {
                    require(files.length() <= MAX_ARCHIVE_ENTRIES) { "Modpack contains too many files" }
                    for (i in 0 until files.length()) {
                        val item = files.optJSONObject(i) ?: continue
                        val env = item.optJSONObject("env")
                        if (env != null && env.optString("client") == "unsupported") continue
                        val path = safeRelative(item.optString("path"))
                        val size = item.optLong("fileSize", -1L)
                        if (size > MAX_FILE_BYTES) throw IOException("Modpack file exceeds safety limit: $path")
                        if (size > 0L) {
                            total += size
                            if (total > MAX_TOTAL_BYTES) throw IOException("Modpack exceeds total safety limit")
                        }
                        val hashes = item.optJSONObject("hashes")
                        val sha1 = hashes?.optString("sha1").orEmpty()
                        require(sha1.matches(Regex("^[A-Fa-f0-9]{40}$"))) { "Missing/invalid SHA-1 for $path" }
                        val downloads = item.optJSONArray("downloads") ?: throw IOException("No download URL for $path")
                        val url = chooseAllowedDownload(downloads) ?: throw IOException("No supported HTTPS download for $path")
                        val destination = File(importRoot, path).canonicalFile
                        require(destination.path.startsWith(importRoot.path + File.separator)) { "Unsafe modpack file path" }
                        ensureParent(destination)
                        downloadVerified(url, destination, sha1, size)
                        downloaded++
                    }
                }

                applyOverrides(staging.resolve("overrides"), importRoot)
                applyOverrides(staging.resolve("client-overrides"), importRoot)
                writeInstanceMetadata(importRoot, name, minecraft, loader)
                replaceTransactionally(target, importRoot)
                return Result(name, minecraft, loader, target, downloaded)
            } catch (t: Throwable) {
                deleteRecursively(importRoot)
                throw t
            }
        } finally {
            deleteRecursively(staging)
        }
    }

    private fun replaceTransactionally(target: File, replacement: File) {
        val parent = target.parentFile ?: throw IOException("Missing modpack parent")
        val backup = File(parent, ".${target.name}.backup-${System.nanoTime()}").canonicalFile
        require(backup.parentFile?.canonicalFile == parent.canonicalFile)
        if (backup.exists()) deleteRecursively(backup)
        var backedUp = false
        try {
            if (target.exists()) {
                if (!target.renameTo(backup)) throw IOException("Could not stage existing modpack for replacement")
                backedUp = true
            }
            if (!replacement.renameTo(target)) throw IOException("Could not finalize modpack installation")
            if (backedUp) deleteRecursively(backup)
        } catch (t: Throwable) {
            if (target.exists()) deleteRecursively(target)
            if (backedUp && backup.exists() && !backup.renameTo(target)) {
                throw IOException("Modpack replacement failed and previous instance could not be restored", t)
            }
            throw t
        } finally {
            if (!target.exists()) deleteRecursively(replacement)
            if (backup.exists() && target.exists()) deleteRecursively(backup)
        }
    }

    private fun detectLoader(dependencies: JSONObject?): MinecraftLoaderProfile.Loader {
        if (dependencies == null) return MinecraftLoaderProfile.Loader.VANILLA
        val keys = dependencies.keys()
        while (keys.hasNext()) {
            when (MinecraftLoaderProfile.parse(keys.next())) {
                MinecraftLoaderProfile.Loader.FABRIC -> return MinecraftLoaderProfile.Loader.FABRIC
                MinecraftLoaderProfile.Loader.NEOFORGE -> return MinecraftLoaderProfile.Loader.NEOFORGE
                MinecraftLoaderProfile.Loader.FORGE -> return MinecraftLoaderProfile.Loader.FORGE
                MinecraftLoaderProfile.Loader.QUILT -> return MinecraftLoaderProfile.Loader.QUILT
                MinecraftLoaderProfile.Loader.VANILLA -> Unit
            }
        }
        return MinecraftLoaderProfile.Loader.VANILLA
    }

    private fun unzip(source: File, staging: File) {
        var total = 0L
        var entries = 0
        ZipInputStream(BufferedInputStream(FileInputStream(source), 64 * 1024)).use { zip ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val entry = zip.nextEntry ?: break
                if (++entries > MAX_ARCHIVE_ENTRIES) throw IOException("Modpack archive has too many entries")
                val name = safeRelative(entry.name)
                val out = File(staging, name).canonicalFile
                require(out.path == staging.path || out.path.startsWith(staging.path + File.separator)) { "Unsafe archive entry" }
                if (entry.isDirectory) {
                    if (!out.exists() && !out.mkdirs() && !out.isDirectory) throw IOException("Could not create $out")
                    continue
                }
                ensureParent(out)
                var fileBytes = 0L
                FileOutputStream(out, false).use { output ->
                    while (true) {
                        val n = zip.read(buffer)
                        if (n < 0) break
                        fileBytes += n
                        total += n
                        if (fileBytes > MAX_FILE_BYTES || total > MAX_TOTAL_BYTES) throw IOException("Modpack archive exceeds safety limit")
                        output.write(buffer, 0, n)
                    }
                    output.fd.sync()
                }
            }
        }
    }

    private fun applyOverrides(source: File, target: File) {
        if (!source.isDirectory) return
        source.walkTopDown().forEach { file ->
            if (file == source) return@forEach
            val relative = source.toPath().relativize(file.toPath()).toString()
            val destination = File(target, relative).canonicalFile
            require(destination.path.startsWith(target.path + File.separator)) { "Unsafe override path" }
            if (file.isDirectory) {
                if (!destination.exists() && !destination.mkdirs() && !destination.isDirectory) {
                    throw IOException("Could not create override directory")
                }
            } else {
                ensureParent(destination)
                FileInputStream(file).use { input ->
                    FileOutputStream(destination, false).use { output ->
                        input.copyTo(output, 64 * 1024)
                        output.fd.sync()
                    }
                }
            }
        }
    }

    private fun chooseAllowedDownload(downloads: org.json.JSONArray): String? {
        for (i in 0 until downloads.length()) {
            val raw = downloads.optString(i).trim()
            try {
                val url = URL(raw)
                if (url.protocol.equals("https", true) && url.host.lowercase() in allowedHosts) return raw
            } catch (_: Throwable) { }
        }
        return null
    }

    private fun downloadVerified(rawUrl: String, target: File, expectedSha1: String, expectedSize: Long) {
        var current = URL(rawUrl)
        repeat(MAX_REDIRECTS + 1) { attempt ->
            require(isAllowedDownloadUrl(current)) { "Untrusted modpack download host" }
            val c = (current.openConnection() as HttpURLConnection).apply {
                connectTimeout = CONNECT_TIMEOUT
                readTimeout = READ_TIMEOUT
                instanceFollowRedirects = false
                requestMethod = "GET"
            }
            try {
                val response = c.responseCode
                if (response in 300..399) {
                    val location = c.getHeaderField("Location")
                    if (location.isNullOrBlank()) throw IOException("Redirect has no Location header")
                    if (attempt >= MAX_REDIRECTS) throw IOException("Too many modpack download redirects")
                    current = URI(current.toString()).resolve(location).toURL()
                    continue
                }
                if (response !in 200..299) throw IOException("HTTP $response while downloading $rawUrl")
                val declared = c.contentLengthLong
                if (declared > MAX_FILE_BYTES) throw IOException("Downloaded file exceeds safety limit")
                val digest = MessageDigest.getInstance("SHA-1")
                var count = 0L
                c.inputStream.use { input ->
                    FileOutputStream(target, false).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val n = input.read(buffer)
                            if (n < 0) break
                            count += n
                            if (count > MAX_FILE_BYTES) throw IOException("Downloaded file exceeds safety limit")
                            digest.update(buffer, 0, n)
                            output.write(buffer, 0, n)
                        }
                        output.fd.sync()
                    }
                }
                if (expectedSize > 0L && count != expectedSize) throw IOException("Size verification failed for ${target.name}")
                val actual = digest.digest().joinToString("") { "%02x".format(it) }
                if (!actual.equals(expectedSha1, true)) throw IOException("SHA-1 verification failed for ${target.name}")
                return
            } finally {
                c.disconnect()
            }
        }
        throw IOException("Modpack download failed")
    }

    private fun isAllowedDownloadUrl(url: URL): Boolean =
        url.protocol.equals("https", true) && url.host.lowercase() in allowedHosts

    private fun writeInstanceMetadata(target: File, name: String, minecraft: String?, loader: MinecraftLoaderProfile.Loader) {
        val json = JSONObject()
            .put("name", name)
            .put("minecraft", minecraft ?: "")
            .put("loader", loader.name.lowercase())
            .put("managedBy", "Droid Launcher")
        File(target, ".droid-launcher-instance.json").writeText(json.toString(2), Charsets.UTF_8)
    }

    private fun safeRelative(raw: String): String {
        val name = raw.replace('\\', '/')
        require(
            name.isNotBlank() &&
                !name.startsWith("/") &&
                !name.contains("../") &&
                !name.contains("..\\") &&
                !name.matches(Regex("^[A-Za-z]:/.*"))
        ) { "Unsafe relative path: $raw" }
        return name
    }

    private fun sanitize(value: String): String =
        value.replace(Regex("[\\\\/:*?\"<>|]"), "_").trim().take(120).ifBlank { "Modpack" }

    private fun ensureParent(file: File) {
        val parent = file.parentFile ?: throw IOException("Missing file parent")
        if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
            throw IOException("Could not create parent directory $parent")
        }
    }

    private fun deleteRecursively(file: File) {
        if (file.isDirectory) file.listFiles()?.forEach(::deleteRecursively)
        if (file.exists() && !file.delete()) throw IOException("Could not delete $file")
    }
}
