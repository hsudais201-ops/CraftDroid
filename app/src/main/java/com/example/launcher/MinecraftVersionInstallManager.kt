package com.example.launcher

import android.content.Context
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.ConcurrentHashMap

/**
 * Downloads and verifies a complete vanilla Minecraft client from the official
 * Mojang/Piston metadata endpoints. Downloads are resumable via .part files and
 * installation state is persisted in SharedPreferences.
 *
 * Finalization is Android-safe: renameTo() is attempted first, then a verified
 * stream-copy fallback is used when a filesystem rejects the rename.
 */
object MinecraftVersionInstallManager {
    private const val PREFS = "droid_launcher"
    private const val MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val RESOURCES_BASE = "https://resources.download.minecraft.net/"
    private const val CONNECT_TIMEOUT_MS = 20_000
    private const val READ_TIMEOUT_MS = 60_000
    private const val BUFFER_SIZE = 64 * 1024
    private const val FINALIZE_ATTEMPTS = 3
    private const val MAX_REDIRECTS = 3
    private const val MAX_TEXT_RESPONSE_BYTES = 4L * 1024L * 1024L
    private const val PROGRESS_PERSIST_INTERVAL_BYTES = 512L * 1024L
    private val VERSION_PATTERN = Regex("^[A-Za-z0-9._+\\-]{1,64}$")

    private val executor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "DroidLauncher-MinecraftInstall").apply {
            isDaemon = true
            priority = Thread.NORM_PRIORITY - 1
        }
    }
    private val cancellations = ConcurrentHashMap.newKeySet<String>()
    private val inFlight = ConcurrentHashMap.newKeySet<String>()
    private val lastProgressPersisted = ConcurrentHashMap<String, Long>()

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
        val safeVersion = normalizeVersionId(version) ?: return State.NOT_INSTALLED
        return try {
            State.valueOf(prefs(context).getString(stateKey(safeVersion), State.NOT_INSTALLED.name)!!)
        } catch (_: Throwable) {
            State.NOT_INSTALLED
        }
    }

    fun isInstalled(context: Context, version: String): Boolean {
        val safeVersion = normalizeVersionId(version) ?: return false
        if (state(context, safeVersion) != State.INSTALLED) return false
        return verifyInstalledArtifacts(context, safeVersion, includeAllAssets = true)
    }

    private fun verifyInstalledArtifacts(
        context: Context,
        version: String,
        includeAllAssets: Boolean
    ): Boolean {
        return try {
            val root = minecraftRoot(context)
            val versionDir = versionRoot(context, version)
            val metadataFile = File(versionDir, "$version.json")
            if (!metadataFile.isFile) return false
            val metadata = JSONObject(metadataFile.readText(Charsets.UTF_8))

            val client = metadata.optJSONObject("downloads")?.optJSONObject("client") ?: return false
            if (!isArtifactHealthy(
                    File(versionDir, "$version.jar"),
                    client.optString("sha1"),
                    client.optLong("size", -1L)
                )
            ) return false

            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    if (!libraryAllowed(library)) continue
                    val downloads = library.optJSONObject("downloads") ?: continue
                    val artifact = downloads.optJSONObject("artifact")
                    if (artifact != null) {
                        val path = artifact.optString("path")
                        if (path.isNotBlank() && !isArtifactHealthy(
                                File(root, "libraries/$path"),
                                artifact.optString("sha1"),
                                artifact.optLong("size", -1L)
                            )
                        ) return false
                    }
                    val classifier = preferredNativeClassifier(library)
                    if (!classifier.isNullOrBlank()) {
                        val entry = downloads.optJSONObject("classifiers")?.optJSONObject(classifier)
                        if (entry != null) {
                            val path = entry.optString("path")
                            if (path.isNotBlank() && !isArtifactHealthy(
                                    File(root, "libraries/$path"),
                                    entry.optString("sha1"),
                                    entry.optLong("size", -1L)
                                )
                            ) return false
                        }
                    }
                }
            }

            if (!includeAllAssets) return true

            val assetIndex = metadata.optJSONObject("assetIndex")
            if (assetIndex != null) {
                val id = assetIndex.optString("id")
                val sha1 = assetIndex.optString("sha1")
                if (id.isBlank()) return false
                val indexFile = File(root, "assets/indexes/$id.json")
                if (!isArtifactHealthy(indexFile, sha1, assetIndex.optLong("size", -1L))) return false

                val objects = JSONObject(indexFile.readText(Charsets.UTF_8)).optJSONObject("objects")
                if (objects != null) {
                    val keys = objects.keys()
                    while (keys.hasNext()) {
                        val obj = objects.optJSONObject(keys.next()) ?: continue
                        val hash = obj.optString("hash")
                        if (!hash.matches(Regex("^[a-fA-F0-9]{40}$"))) return false
                        val target = File(root, "assets/objects/" + hash.substring(0, 2) + "/" + hash)
                        if (!isArtifactHealthy(target, hash, obj.optLong("size", -1L))) return false
                    }
                }
            }
            true
        } catch (_: Throwable) {
            false
        }
    }

    /** Full pre-launch validation matching the installer selection rules. */
    fun isLaunchReady(context: Context, version: String): Boolean {
        if (!isInstalled(context, version)) return false
        return try {
            val root = minecraftRoot(context)
            val versionDir = versionRoot(context, version)
            val metadataFile = File(versionDir, "$version.json")
            val metadata = JSONObject(metadataFile.readText(Charsets.UTF_8))
            if (!verifyInstalledArtifacts(context, version, includeAllAssets = true)) return false
            val client = metadata.optJSONObject("downloads")?.optJSONObject("client") ?: return false
            if (!isArtifactHealthy(File(versionDir, "$version.jar"), client.optString("sha1"), client.optLong("size", -1L))) return false

            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    if (!libraryAllowed(library)) continue
                    val downloads = library.optJSONObject("downloads") ?: continue
                    val artifact = downloads.optJSONObject("artifact")
                    if (artifact != null) {
                        val path = artifact.optString("path")
                        if (path.isNotBlank() && !isArtifactHealthy(
                                File(root, "libraries/$path"),
                                artifact.optString("sha1"),
                                artifact.optLong("size", -1L)
                            )
                        ) return false
                    }
                    val classifier = preferredNativeClassifier(library)
                    if (!classifier.isNullOrBlank()) {
                        val entry = downloads.optJSONObject("classifiers")?.optJSONObject(classifier)
                        if (entry != null) {
                            val path = entry.optString("path")
                            if (path.isNotBlank() && !isArtifactHealthy(
                                    File(root, "libraries/$path"),
                                    entry.optString("sha1"),
                                    entry.optLong("size", -1L)
                                )
                            ) return false
                        }
                    }
                }
            }

            val assetIndex = metadata.optJSONObject("assetIndex")
            if (assetIndex != null) {
                val id = assetIndex.optString("id")
                val sha1 = assetIndex.optString("sha1")
                if (id.isBlank()) return false
                val indexFile = File(root, "assets/indexes/$id.json")
                if (!isArtifactHealthy(indexFile, sha1, assetIndex.optLong("size", -1L))) return false

                val objects = JSONObject(indexFile.readText(Charsets.UTF_8)).optJSONObject("objects")
                if (objects != null) {
                    val keys = objects.keys()
                    while (keys.hasNext()) {
                        val obj = objects.optJSONObject(keys.next()) ?: continue
                        val hash = obj.optString("hash")
                        if (!hash.matches(Regex("^[a-fA-F0-9]{40}$"))) return false
                        val target = File(root, "assets/objects/${hash.substring(0, 2)}/$hash")
                        if (!isArtifactHealthy(target, hash, obj.optLong("size", -1L))) return false
                    }
                }
            }
            true
        } catch (_: Throwable) {
            false
        }
    }

    private fun libraryAllowed(lib: JSONObject): Boolean {
        val rules = lib.optJSONArray("rules") ?: return true
        var allowed = false
        for (i in 0 until rules.length()) {
            val rule = rules.optJSONObject(i) ?: continue
            val action = rule.optString("action", "allow").equals("allow", ignoreCase = true)
            val os = rule.optJSONObject("os")
            val osName = os?.optString("name")?.trim().orEmpty()
            val arch = os?.optString("arch")?.trim().orEmpty()
            val currentArch = System.getProperty("os.arch", "").lowercase()
            val osMatches = osName.isBlank() || osName.equals("linux", ignoreCase = true)
            val archMatches = arch.isBlank() || currentArch.contains(arch.lowercase())
            if (osMatches && archMatches) allowed = action
        }
        return allowed
    }

    private fun preferredNativeClassifier(lib: JSONObject): String? {
        val classifiers = lib.optJSONObject("downloads")?.optJSONObject("classifiers") ?: return null
        val names = classifiers.keys().asSequence().toList()
        return when {
            names.contains("natives-linux") -> "natives-linux"
            names.any { it.startsWith("natives-linux-") } -> names.firstOrNull { it.startsWith("natives-linux-") }
            else -> null
        }
    }

    fun lastError(context: Context, version: String): String? {
        val safeVersion = normalizeVersionId(version) ?: return null
        return prefs(context).getString(errorKey(safeVersion), null)
    }

    fun cancel(context: Context, version: String) {
        val safeVersion = normalizeVersionId(version) ?: return
        cancellations.add(safeVersion)
        setState(context, safeVersion, State.FAILED, "Installation cancelled")
    }

    fun isCancellationRequested(version: String): Boolean =
        normalizeVersionId(version)?.let(cancellations::contains) == true

    fun install(context: Context, version: String, listener: Listener? = null) {
        val safeVersion = normalizeVersionId(version)
        if (safeVersion == null) {
            listener?.onError(version, IllegalArgumentException("Invalid Minecraft version id"))
            return
        }
        if (isInstalled(context, safeVersion)) {
            listener?.onComplete(safeVersion)
            return
        }
        if (!inFlight.add(safeVersion)) return
        cancellations.remove(safeVersion)
        executor.execute {
            try {
                android.os.Process.setThreadPriority(android.os.Process.THREAD_PRIORITY_BACKGROUND)
                setState(context, safeVersion, State.DOWNLOADING, null)
                installInternal(context, safeVersion, listener)
                if (!verifyInstalledArtifacts(context, safeVersion, includeAllAssets = true)) {
                    throw IOException("Minecraft installation completed downloads but final artifact verification failed")
                }
                setState(context, safeVersion, State.INSTALLED, null)
                persistProgress(context, safeVersion, Long.MAX_VALUE, Long.MAX_VALUE, "Installed")
                lastProgressPersisted.remove(safeVersion)
                cancellations.remove(safeVersion)
                listener?.onComplete(safeVersion)
            } catch (t: Throwable) {
                setState(context, safeVersion, State.FAILED, t.message ?: t.javaClass.simpleName)
                lastProgressPersisted.remove(safeVersion)
                listener?.onError(safeVersion, t)
            } finally {
                inFlight.remove(safeVersion)
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

        report(context, listener, version, 0, 0, "Reading Mojang version manifest")
        val manifest = JSONObject(httpText(MANIFEST_URL))
        val versionEntry = findVersionEntry(manifest, version)
            ?: throw IOException("Minecraft version $version was not found in the official manifest")
        val versionUrl = versionEntry.optString("url")
        requireHttps(versionUrl, "version metadata")

        report(context, listener, version, 0, 0, "Downloading version metadata")
        val metadataRaw = httpText(versionUrl)
        val expectedMetadataSha1 = versionEntry.optString("sha1")
        val expectedMetadataSize = versionEntry.optLong("size", -1L)
        val metadataBytes = metadataRaw.toByteArray(Charsets.UTF_8)
        if (expectedMetadataSha1.isNotBlank() && !sha1Bytes(metadataBytes).equals(expectedMetadataSha1, true)) {
            throw IOException("Version metadata SHA-1 verification failed for $version")
        }
        if (expectedMetadataSize > 0L && metadataBytes.size.toLong() != expectedMetadataSize) {
            throw IOException("Version metadata size verification failed for $version")
        }
        val metadata = JSONObject(metadataRaw)
        writeVerifiedText(File(versionDir, "$version.json"), metadataRaw, expectedMetadataSha1.takeIf { it.isNotBlank() })

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
                val nativeClassifier = preferredNativeClassifier(lib)
                if (!nativeClassifier.isNullOrBlank()) {
                    val entry = libDownloads.optJSONObject("classifiers")?.optJSONObject(nativeClassifier)
                    if (entry != null) {
                        val path = entry.optString("path")
                        if (path.isNotBlank()) {
                            tasks += taskFromDownload(
                                root,
                                File(root, "libraries/$path"),
                                entry,
                                "Native library $path"
                            )
                        }
                    }
                }
            }
        }

        var totalBytes = 0L
        for (task in tasks) totalBytes += task.size.coerceAtLeast(0L)
        var completedBytes = 0L
        report(context, listener, version, completedBytes, totalBytes, "Installing ${tasks.size} Mojang artifacts")
        for (task in tasks) {
            downloadResumable(task, version) { done, total ->
                report(context, listener, version, completedBytes + done, totalBytes.coerceAtLeast(completedBytes + total), "Downloading ${task.label}")
            }
            completedBytes += task.size.coerceAtLeast(fileLength(task.target))
            report(context, listener, version, completedBytes, totalBytes, "Verified ${task.label}")
        }

        val assetIndex = metadata.optJSONObject("assetIndex")
        if (assetIndex != null) {
            val id = assetIndex.optString("id")
            val url = assetIndex.optString("url")
            val sha1 = assetIndex.optString("sha1")
            if (id.isBlank() || url.isBlank()) throw IOException("Invalid asset index metadata")
            requireHttps(url, "asset index")
            val indexFile = File(root, "assets/indexes/$id.json")
            downloadResumable(DownloadTask(indexFile, url, sha1, assetIndex.optLong("size", -1L), "Asset index $id"), version) { done, total ->
                report(context, listener, version, done, total, "Downloading asset index $id")
            }
            val index = JSONObject(indexFile.readText(Charsets.UTF_8))
            val objects = index.optJSONObject("objects")
            if (objects != null) {
                val keys = objects.keys()
                while (keys.hasNext()) {
                    val name = keys.next()
                    val obj = objects.optJSONObject(name) ?: continue
                    val hash = obj.optString("hash")
                    if (!hash.matches(Regex("^[a-fA-F0-9]{40}$"))) continue
                    val target = File(root, "assets/objects/${hash.substring(0, 2)}/$hash")
                    val urlObj = RESOURCES_BASE + hash.substring(0, 2) + "/" + hash
                    downloadResumable(DownloadTask(target, urlObj, hash, obj.optLong("size", -1L), "Asset $name"), version) { done, total ->
                        report(context, listener, version, done, total, "Downloading asset $name")
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
        requireHttps(url, label)
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
        if (task.size > 0L && part.isFile && part.length() > task.size) part.delete()

        var lastError: Throwable? = null
        repeat(4) { attempt ->
            var resume = if (part.isFile) part.length() else 0L
            if (task.size > 0L && resume >= task.size) resume = 0L
            var connection: HttpURLConnection? = null
            try {
                connection = openDownloadConnection(task.url, resume)
                var responseCode = connection.responseCode
                if (resume > 0L && responseCode != HttpURLConnection.HTTP_PARTIAL) {
                    connection.disconnect()
                    connection = openDownloadConnection(task.url, 0L)
                    resume = 0L
                    if (part.exists() && !part.delete()) throw IOException("Could not reset incomplete download for ${task.label}")
                    responseCode = connection.responseCode
                }
                if (responseCode !in 200..299) throw IOException("Download failed: HTTP $responseCode for ${task.label}")

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
                            if (isCancellationRequested(version)) throw IOException("Installation cancelled")
                            val count = input.read(buffer)
                            if (count < 0) break
                            if (count == 0) continue
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
                    throw IOException("SHA-1 verification failed for ${task.label}")
                }
                finalizeVerifiedFile(part, task.target, task.label, task.sha1, task.size)
                return
            } catch (t: Throwable) {
                if (isCancellationRequested(version)) throw t
                lastError = t
                if (attempt + 1 < 4) Thread.sleep(500L * (attempt + 1))
            } finally {
                connection?.disconnect()
            }
        }
        throw IOException("Download could not be completed for ${task.label} after 4 attempts", lastError)
    }

    private fun openDownloadConnection(rawUrl: String, resume: Long): HttpURLConnection {
        var current = try { URL(rawUrl) } catch (_: Throwable) {
            throw IOException("Invalid URL for download")
        }
        repeat(MAX_REDIRECTS + 1) { attempt ->
            requireOfficialMinecraftUrl(current, "download")
            val connection = (current.openConnection() as HttpURLConnection).apply {
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                instanceFollowRedirects = false
                requestMethod = "GET"
                if (resume > 0L) setRequestProperty("Range", "bytes=$resume-")
            }
            val responseCode = connection.responseCode
            if (responseCode !in 300..399) return connection
            val location = connection.getHeaderField("Location")
            connection.disconnect()
            if (location.isNullOrBlank()) throw IOException("Redirect has no Location header")
            if (attempt >= MAX_REDIRECTS) throw IOException("Too many redirects for download")
            current = try { URI(current.toString()).resolve(location).toURL() } catch (_: Throwable) {
                throw IOException("Invalid download redirect target")
            }
        }
        throw IOException("Redirect resolution failed for download")
    }

    private fun requireHttps(rawUrl: String, label: String) {
        val parsed = try { URL(rawUrl) } catch (_: Throwable) { throw IOException("Invalid URL for $label") }
        requireOfficialMinecraftUrl(parsed, label)
    }

    private fun requireOfficialMinecraftUrl(url: URL, label: String) {
        if (!url.protocol.equals("https", ignoreCase = true)) {
            throw IOException("Non-HTTPS URL rejected for $label")
        }
        val host = url.host.lowercase()
        val official =
            host == "piston-meta.mojang.com" ||
            host == "piston-data.mojang.com" ||
            host == "launcher.mojang.com" ||
            host == "libraries.minecraft.net" ||
            host == "resources.download.minecraft.net" ||
            host.endsWith(".mojang.com") ||
            host.endsWith(".minecraft.net")
        if (!official) throw IOException("Untrusted Minecraft download host for $label: $host")
    }

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
                if (!part.delete() && part.exists()) throw IOException("Finalized $label but could not remove temporary file")
                return
            }
            try {
                if (target.exists() && !target.delete() && target.exists()) {
                    throw IOException("Could not replace existing destination ${target.absolutePath}")
                }
                if (part.renameTo(target) && isArtifactHealthy(target, expectedSha1, expectedSize)) return
                if (target.exists() && !target.delete() && target.exists()) throw IOException("Could not clear failed destination ${target.absolutePath}")
                copyFileAndSync(part, target)
                if (!isArtifactHealthy(target, expectedSha1, expectedSize)) {
                    target.delete()
                    throw IOException("Destination verification failed while finalizing $label")
                }
                if (!part.delete() && part.exists()) throw IOException("Finalized $label but could not remove temporary file")
                return
            } catch (t: Throwable) {
                lastError = t
                if (attempt + 1 < FINALIZE_ATTEMPTS) Thread.sleep(100L * (attempt + 1))
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
        return digest.digest().joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }
    }

    private fun sha1Bytes(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-1")
        return digest.digest(bytes).joinToString("") { "%02x".format(it) }
    }

    private fun writeVerifiedText(target: File, content: String, sha1: String?) {
        target.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) throw IOException("Could not create metadata directory ${parent.absolutePath}")
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
        requireHttps(url, "HTTP request")
        val connection = openDownloadConnection(url, 0L)
        return try {
            val code = connection.responseCode
            if (code !in 200..299) throw IOException("HTTP $code for $url")
            BufferedInputStream(connection.inputStream, BUFFER_SIZE).use { input ->
                val output = ByteArrayOutputStream()
                val buffer = ByteArray(BUFFER_SIZE)
                var total = 0L
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    total += count
                    if (total > MAX_TEXT_RESPONSE_BYTES) {
                        throw IOException("HTTP response exceeds safety limit")
                    }
                    output.write(buffer, 0, count)
                }
                output.toByteArray().toString(Charsets.UTF_8)
            }
        } finally {
            connection.disconnect()
        }
    }

    private fun findVersionEntry(manifest: JSONObject, version: String): JSONObject? {
        val versions = manifest.optJSONArray("versions") ?: return null
        for (i in 0 until versions.length()) {
            val item = versions.optJSONObject(i) ?: continue
            if (item.optString("id") == version) return item
        }
        return null
    }

    private fun minecraftRoot(context: Context): File = File(context.filesDir, "minecraft").apply { mkdirs() }
    private fun versionRoot(context: Context, version: String): File {
        val safeVersion = requireVersionId(version)
        return File(minecraftRoot(context), "versions/$safeVersion").apply { mkdirs() }
    }

    private fun normalizeVersionId(raw: String): String? =
        raw.trim().takeIf { VERSION_PATTERN.matches(it) }

    private fun requireVersionId(raw: String): String =
        normalizeVersionId(raw) ?: throw IllegalArgumentException("Invalid Minecraft version id")
    private fun fileLength(file: File): Long = if (file.isFile) file.length() else 0L
    private fun prefs(context: Context) = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private fun stateKey(version: String) = "mc_install_${version}_state"
    private fun errorKey(version: String) = "mc_install_${version}_error"

    private fun setState(context: Context, version: String, state: State, error: String?) {
        prefs(context).edit().putString(stateKey(version), state.name).putString(errorKey(version), error).apply()
    }

    private fun report(context: Context, listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {
        val safeDownloaded = downloaded.coerceAtLeast(0L)
        val safeTotal = total.coerceAtLeast(safeDownloaded)
        val safeStage = stage.take(180)
        val previous = lastProgressPersisted[version] ?: -1L
        if (previous < 0L ||
            safeDownloaded == safeTotal ||
            safeDownloaded - previous >= PROGRESS_PERSIST_INTERVAL_BYTES
        ) {
            persistProgress(context, version, safeDownloaded, safeTotal, safeStage)
            lastProgressPersisted[version] = safeDownloaded
        }
        listener?.onProgress(Progress(version, safeDownloaded, safeTotal, safeStage, State.DOWNLOADING))
    }

    private fun persistProgress(context: Context, version: String, downloaded: Long, total: Long, stage: String) {
        val persistedDownloaded = if (downloaded == Long.MAX_VALUE) {
            prefs(context).getLong(progressKey(version), 0L)
        } else downloaded
        val persistedTotal = if (total == Long.MAX_VALUE) {
            prefs(context).getLong(totalKey(version), 0L)
        } else total.coerceAtLeast(persistedDownloaded)
        prefs(context).edit()
            .putLong(progressKey(version), persistedDownloaded.coerceAtLeast(0L))
            .putLong(totalKey(version), persistedTotal.coerceAtLeast(0L))
            .putString(stageKey(version), stage.take(180))
            .apply()
    }
    fun savedProgress(context: Context, version: String): Progress {
        val safeVersion = normalizeVersionId(version) ?: version.trim()
        val p = prefs(context)
        return Progress(
            safeVersion,
            p.getLong(progressKey(safeVersion), 0L),
            p.getLong(totalKey(safeVersion), 0L),
            p.getString(stageKey(safeVersion), "Ready") ?: "Ready",
            state(context, safeVersion)
        )
    }

    private fun progressKey(version: String) = "mc_install_${version}_downloaded"
    private fun totalKey(version: String) = "mc_install_${version}_total"
    private fun stageKey(version: String) = "mc_install_${version}_stage"

}
