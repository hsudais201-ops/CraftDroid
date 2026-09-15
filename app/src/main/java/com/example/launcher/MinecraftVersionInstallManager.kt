package com.example.launcher

import android.content.Context
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.Executors

/**
 * Downloads and verifies a complete vanilla Minecraft client from the official
 * Mojang/Piston metadata endpoints. Downloads are resumable via .part files and
 * installation state is persisted in SharedPreferences.
 *
 * Finalization is deliberately Android-safe: File.renameTo() is attempted first,
 * but a verified stream-copy fallback is used when Android/filesystem semantics
 * reject the rename. This is important for the assets/objects tree on some
 * Android storage/filesystem combinations.
 */
object MinecraftVersionInstallManager {
    private const val PREFS = "droid_launcher"
    private const val MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val RESOURCES_BASE = "https://resources.download.minecraft.net/"
    private const val CONNECT_TIMEOUT_MS = 20_000
    private const val READ_TIMEOUT_MS = 60_000
    private const val BUFFER_SIZE = 64 * 1024
    private const val FINALIZE_ATTEMPTS = 3

    private val executor = Executors.newCachedThreadPool()

    enum class State { NOT_INSTALLED, DOWNLOADING, INSTALLED, FAILED }

    data class Progress(
        val version: String,
        val downloaded: Long,
        val total: Long,
        val stage: String,
        val state: State
    )

    interface Listener {
        fun onProgress(progress: Progress)
        fun onComplete(version: String)
        fun onError(version: String, error: Throwable)
    }

    fun state(context: Context, version: String): State {
        return try {
            State.valueOf(prefs(context).getString(stateKey(version), State.NOT_INSTALLED.name)!!)
        } catch (_: Throwable) {
            State.NOT_INSTALLED
        }
    }

    fun isInstalled(context: Context, version: String): Boolean {
        if (state(context, version) != State.INSTALLED) return false
        val root = versionRoot(context, version)
        val client = File(root, "$version.jar")
        return client.isFile && client.length() > 0L && File(root, "$version.json").isFile
    }

    fun lastError(context: Context, version: String): String? =
        prefs(context).getString(errorKey(version), null)

    fun install(context: Context, version: String, listener: Listener? = null) {
        if (version.isBlank()) {
            listener?.onError(version, IllegalArgumentException("Minecraft version is empty"))
            return
        }
        if (isInstalled(context, version)) {
            listener?.onComplete(version)
            return
        }
        executor.execute {
            try {
                setState(context, version, State.DOWNLOADING, null)
                installInternal(context, version, listener)
                setState(context, version, State.INSTALLED, null)
                listener?.onComplete(version)
            } catch (t: Throwable) {
                setState(context, version, State.FAILED, t.message ?: t.javaClass.simpleName)
                listener?.onError(version, t)
            }
        }
    }

    private fun installInternal(context: Context, version: String, listener: Listener?) {
        val root = minecraftRoot(context)
        val versionDir = versionRoot(context, version)
        versionDir.mkdirs()
        File(root, "libraries").mkdirs()
        File(root, "assets/indexes").mkdirs()
        File(root, "assets/objects").mkdirs()

        report(listener, version, 0, 0, "Reading Mojang version manifest")
        val manifest = JSONObject(httpText(MANIFEST_URL))
        val versionUrl = findVersionUrl(manifest, version)
            ?: throw IOException("Minecraft version $version was not found in the official manifest")

        report(listener, version, 0, 0, "Downloading version metadata")
        val metadata = JSONObject(httpText(versionUrl))
        writeVerifiedText(File(versionDir, "$version.json"), metadata.toString(), null)

        val tasks = ArrayList<DownloadTask>()

        val downloads = metadata.optJSONObject("downloads")
        val client = downloads?.optJSONObject("client")
        if (client != null) {
            tasks += taskFromDownload(root, File(versionDir, "$version.jar"), client, "Minecraft client")
        } else {
            throw IOException("Version metadata has no client download for $version")
        }

        val libraries = metadata.optJSONArray("libraries")
        if (libraries != null) {
            for (i in 0 until libraries.length()) {
                val lib = libraries.optJSONObject(i) ?: continue
                val libDownloads = lib.optJSONObject("downloads") ?: continue
                val artifact = libDownloads.optJSONObject("artifact")
                if (artifact != null) {
                    val path = artifact.optString("path")
                    if (path.isNotBlank()) {
                        tasks += taskFromDownload(root, File(root, "libraries/$path"), artifact, "Library $path")
                    }
                }
                val classifiers = libDownloads.optJSONObject("classifiers")
                if (classifiers != null) {
                    val keys = classifiers.keys()
                    while (keys.hasNext()) {
                        val classifier = keys.next()
                        val entry = classifiers.optJSONObject(classifier) ?: continue
                        val path = entry.optString("path")
                        if (path.isNotBlank()) {
                            tasks += taskFromDownload(root, File(root, "libraries/$path"), entry, "Native library $path")
                        }
                    }
                }
            }
        }

        var totalBytes = 0L
        for (task in tasks) totalBytes += task.size.coerceAtLeast(0L)
        var completedBytes = 0L
        report(listener, version, completedBytes, totalBytes, "Installing ${tasks.size} Mojang artifacts")
        for (task in tasks) {
            downloadResumable(task, version) { done, total ->
                report(listener, version, completedBytes + done, totalBytes.coerceAtLeast(completedBytes + total), "Downloading ${task.label}")
            }
            completedBytes += task.size.coerceAtLeast(fileLength(task.target))
            report(listener, version, completedBytes, totalBytes, "Verified ${task.label}")
        }

        val assetIndex = metadata.optJSONObject("assetIndex")
        if (assetIndex != null) {
            val id = assetIndex.optString("id")
            val url = assetIndex.optString("url")
            val sha1 = assetIndex.optString("sha1")
            if (id.isBlank() || url.isBlank()) throw IOException("Invalid asset index metadata")
            val indexFile = File(root, "assets/indexes/$id.json")
            downloadResumable(DownloadTask(indexFile, url, sha1, assetIndex.optLong("size", -1L), "Asset index $id"), version) { done, total ->
                report(listener, version, done, total, "Downloading asset index $id")
            }
            val index = JSONObject(indexFile.readText(Charsets.UTF_8))
            val objects = index.optJSONObject("objects")
            if (objects != null) {
                val keys = objects.keys()
                while (keys.hasNext()) {
                    val name = keys.next()
                    val obj = objects.optJSONObject(name) ?: continue
                    val hash = obj.optString("hash")
                    if (hash.length < 3) continue
                    val target = File(root, "assets/objects/${hash.substring(0, 2)}/$hash")
                    val urlObj = RESOURCES_BASE + hash.substring(0, 2) + "/" + hash
                    downloadResumable(DownloadTask(target, urlObj, hash, obj.optLong("size", -1L), "Asset $name"), version) { done, total ->
                        report(listener, version, done, total, "Downloading asset $name")
                    }
                }
            }
        }

        if (!isArtifactHealthy(File(versionDir, "$version.jar"), client.optString("sha1"), client.optLong("size", -1L))) {
            throw IOException("Final client JAR verification failed")
        }
    }

    private data class DownloadTask(
        val target: File,
        val url: String,
        val sha1: String,
        val size: Long,
        val label: String
    )

    private fun taskFromDownload(root: File, target: File, obj: JSONObject, label: String): DownloadTask {
        val url = obj.optString("url")
        val sha1 = obj.optString("sha1")
        val size = obj.optLong("size", -1L)
        if (url.isBlank()) throw IOException("Missing download URL for $label")
        val canonical = target.canonicalFile
        require(canonical.path.startsWith(root.canonicalPath + File.separator) || canonical == root.canonicalFile) {
            "Unsafe artifact path: $target"
        }
        return DownloadTask(canonical, url, sha1, size, label)
    }

    private fun downloadResumable(task: DownloadTask, version: String, onProgress: (Long, Long) -> Unit) {
        task.target.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                throw IOException("Could not create directory ${parent.absolutePath} for ${task.label}")
            }
        }
        if (isArtifactHealthy(task.target, task.sha1, task.size)) {
            onProgress(task.target.length(), task.size.coerceAtLeast(task.target.length()))
            return
        }

        val parent = task.target.parentFile ?: throw IOException("Missing parent directory for ${task.target}")
        val part = File(parent, task.target.name + ".part")
        var resume = if (part.isFile) part.length() else 0L
        var connection: HttpURLConnection? = null
        try {
            connection = openDownloadConnection(task.url, resume)
            var responseCode = connection.responseCode
            if (resume > 0L && responseCode != HttpURLConnection.HTTP_PARTIAL) {
                connection.disconnect()
                connection = openDownloadConnection(task.url, 0L)
                resume = 0L
                part.delete()
                responseCode = connection.responseCode
            }

            if (responseCode !in 200..299) {
                throw IOException("Download failed: HTTP $responseCode for ${task.label}")
            }

            val append = resume > 0L && responseCode == HttpURLConnection.HTTP_PARTIAL
            if (!append) resume = 0L

            val expectedTotal = when {
                task.size > 0L -> task.size
                append -> resume + connection.contentLengthLong.coerceAtLeast(0L)
                connection.contentLengthLong > 0L -> connection.contentLengthLong
                else -> -1L
            }

            BufferedInputStream(connection.inputStream, BUFFER_SIZE).use { input ->
                FileOutputStream(part, append).use { output ->
                    val buffer = ByteArray(BUFFER_SIZE)
                    var downloaded = resume
                    while (true) {
                        val count = input.read(buffer)
                        if (count < 0) break
                        output.write(buffer, 0, count)
                        downloaded += count
                        onProgress(downloaded, expectedTotal)
                    }
                    output.fd.sync()
                }
            }

            if (expectedTotal > 0L && part.length() != expectedTotal) {
                throw IOException("Incomplete download for ${task.label}: ${part.length()}/$expectedTotal")
            }
            if (!isArtifactHealthy(part, task.sha1, task.size)) {
                part.delete()
                throw IOException("SHA-1 verification failed for ${task.label}")
            }

            finalizeVerifiedFile(part, task.target, task.label, task.sha1, task.size)
        } finally {
            connection?.disconnect()
        }
    }

    private fun openDownloadConnection(url: String, resume: Long): HttpURLConnection =
        (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            instanceFollowRedirects = true
            requestMethod = "GET"
            if (resume > 0L) setRequestProperty("Range", "bytes=$resume-")
        }

    /**
     * Finalizes a fully verified .part file without relying solely on File.renameTo().
     * Android vendors/filesystems can return false from renameTo() even when both
     * files live in the same app-private tree. The fallback copies the already
     * verified bytes into the destination, fsyncs them, verifies the destination,
     * and only then removes the .part file.
     */
    private fun finalizeVerifiedFile(
        part: File,
        target: File,
        label: String,
        expectedSha1: String,
        expectedSize: Long
    ) {
        target.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                throw IOException("Could not create destination directory ${parent.absolutePath} for $label")
            }
        }

        var lastError: Throwable? = null
        repeat(FINALIZE_ATTEMPTS) { attempt ->
            if (isArtifactHealthy(target, expectedSha1, expectedSize)) {
                if (!part.delete() && part.exists()) {
                    throw IOException("Finalized $label but could not remove temporary file")
                }
                return
            }

            try {
                if (target.exists() && !target.delete() && target.exists()) {
                    // Do not overwrite the destination with the fallback while a
                    // stale file cannot be removed; retrying may still recover.
                    throw IOException("Could not replace existing destination ${target.absolutePath}")
                }

                if (part.renameTo(target) && isArtifactHealthy(target, expectedSha1, expectedSize)) {
                    return
                }

                // renameTo() failed or produced a destination that cannot be verified.
                // Re-create the destination via a streamed copy from the verified part.
                if (target.exists() && !target.delete() && target.exists()) {
                    throw IOException("Could not clear failed destination ${target.absolutePath}")
                }
                copyFileAndSync(part, target)
                if (!isArtifactHealthy(target, expectedSha1, expectedSize)) {
                    target.delete()
                    throw IOException("Destination verification failed while finalizing $label")
                }
                if (!part.delete() && part.exists()) {
                    throw IOException("Finalized $label but could not remove temporary file")
                }
                return
            } catch (t: Throwable) {
                lastError = t
                if (attempt + 1 < FINALIZE_ATTEMPTS) {
                    Thread.sleep((100L * (attempt + 1)))
                }
            }
        }

        throw IOException("Could not finalize ${target.absolutePath} for $label after $FINALIZE_ATTEMPTS attempts", lastError)
    }

    private fun copyFileAndSync(source: File, target: File) {
        BufferedInputStream(FileInputStream(source), BUFFER_SIZE).use { input ->
            FileOutputStream(target, false).use { output ->
                val buffer = ByteArray(BUFFER_SIZE)
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    output.write(buffer, 0, count)
                }
                output.fd.sync()
            }
        }
    }

    private fun isArtifactHealthy(file: File, expectedSha1: String, expectedSize: Long): Boolean {
        if (!file.isFile || file.length() <= 0L) return false
        if (expectedSize > 0L && file.length() != expectedSize) return false
        if (expectedSha1.isBlank()) return expectedSize <= 0L || file.length() == expectedSize
        return sha1(file).equals(expectedSha1, ignoreCase = true)
    }

    private fun sha1(file: File): String {
        val digest = MessageDigest.getInstance("SHA-1")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun writeVerifiedText(target: File, content: String, sha1: String?) {
        target.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                throw IOException("Could not create metadata directory ${parent.absolutePath}")
            }
        }
        val part = File(target.parentFile, target.name + ".part")
        part.writeText(content, Charsets.UTF_8)
        if (!sha1.isNullOrBlank() && !sha1(part).equals(sha1, true)) {
            part.delete()
            throw IOException("SHA-1 verification failed for ${target.name}")
        }
        finalizeVerifiedFile(part, target, target.name, sha1.orEmpty(), content.toByteArray(Charsets.UTF_8).size.toLong())
    }

    private fun httpText(url: String): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
            connectTimeout = CONNECT_TIMEOUT_MS
            readTimeout = READ_TIMEOUT_MS
            instanceFollowRedirects = true
            requestMethod = "GET"
        }
        return try {
            val code = connection.responseCode
            if (code !in 200..299) throw IOException("HTTP $code for $url")
            BufferedInputStream(connection.inputStream, BUFFER_SIZE).use { it.readBytes().toString(Charsets.UTF_8) }
        } finally {
            connection.disconnect()
        }
    }

    private fun findVersionUrl(manifest: JSONObject, version: String): String? {
        val versions = manifest.optJSONArray("versions") ?: return null
        for (i in 0 until versions.length()) {
            val item = versions.optJSONObject(i) ?: continue
            if (item.optString("id") == version) return item.optString("url").takeIf { it.isNotBlank() }
        }
        return null
    }

    private fun minecraftRoot(context: Context): File =
        File(context.filesDir, "minecraft").apply { mkdirs() }

    private fun versionRoot(context: Context, version: String): File =
        File(minecraftRoot(context), "versions/$version").apply { mkdirs() }

    private fun fileLength(file: File): Long = if (file.isFile) file.length() else 0L

    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    private fun stateKey(version: String) = "mc_install_${version}_state"
    private fun errorKey(version: String) = "mc_install_${version}_error"

    private fun setState(context: Context, version: String, state: State, error: String?) {
        prefs(context).edit()
            .putString(stateKey(version), state.name)
            .putString(errorKey(version), error)
            .apply()
    }

    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {
        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))
    }
}
