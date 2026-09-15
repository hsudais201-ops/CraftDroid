package com.example.launcher

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URI
import java.security.MessageDigest
import java.util.concurrent.Executors

/**
 * Checks the public CraftDroid GitHub Releases API for a newer Droid Launcher
 * APK. The updater requires a SHA-256 sidecar and verifies it before returning
 * an update file. Network callbacks are marshalled back to the Android main thread.
 */
object DroidLauncherUpdateManager {
    private const val API_URL = "https://api.github.com/repos/hsudais201-ops/CraftDroid/releases/latest"
    private const val PREFS = "droid_launcher_updates"
    private const val LAST_CHECK = "last_check_ms"
    private const val CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000L
    private const val MAX_APK_BYTES = 512L * 1024L * 1024L
    private const val MAX_TEXT_BYTES = 2L * 1024L * 1024L
    private const val MAX_REDIRECTS = 3
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    data class Release(val tag: String, val apkUrl: String, val sha256Url: String)

    fun shouldCheck(context: Context): Boolean =
        System.currentTimeMillis() - context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getLong(LAST_CHECK, 0L) >= CHECK_INTERVAL_MS

    fun check(context: Context, onResult: (Release?) -> Unit) {
        executor.execute {
            val result = try { fetchLatest() } catch (_: Throwable) { null }
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putLong(LAST_CHECK, System.currentTimeMillis()).apply()
            mainHandler.post { onResult(result) }
        }
    }

    fun downloadVerified(context: Context, release: Release): File {
        val updateDir = File(context.cacheDir, "launcher-updates").canonicalFile
        if (!updateDir.exists() && !updateDir.mkdirs() && !updateDir.isDirectory) {
            throw IllegalStateException("Could not create update cache")
        }
        val apk = File(updateDir, "droid-launcher-${sanitize(release.tag)}.apk").canonicalFile
        require(apk.parentFile?.canonicalFile == updateDir) { "Unsafe update path" }
        download(release.apkUrl, apk, MAX_APK_BYTES)

        val expected = downloadText(release.sha256Url)
            .trim()
            .split(Regex("\\s+"))
            .firstOrNull()
            ?.takeIf { it.matches(Regex("^[A-Fa-f0-9]{64}$")) }
            ?: throw IllegalStateException("Invalid or missing launcher update SHA-256")
        val actual = sha256(apk)
        require(actual.equals(expected, ignoreCase = true)) {
            "Launcher update SHA-256 verification failed"
        }
        require(apk.isFile && apk.length() > 0L) { "Downloaded launcher update is empty" }
        return apk
    }

    private fun fetchLatest(): Release? {
        val json = org.json.JSONObject(downloadText(API_URL))
        val tag = json.optString("tag_name").trim().ifBlank { return null }
        if (json.optBoolean("draft", false) || json.optBoolean("prerelease", false)) return null
        val assets = json.optJSONArray("assets") ?: return null
        var apk: String? = null
        var sha: String? = null
        for (i in 0 until assets.length()) {
            val asset = assets.optJSONObject(i) ?: continue
            val name = asset.optString("name")
            val url = asset.optString("browser_download_url")
            if (name.endsWith(".apk", true) && isGithubDownloadUrl(url)) apk = url
            if (name.endsWith(".sha256", true) && isGithubDownloadUrl(url)) sha = url
        }
        val apkUrl = apk ?: return null
        val shaUrl = sha ?: return null
        return Release(tag, apkUrl, shaUrl)
    }

    private fun downloadText(rawUrl: String): String {
        val c = open(rawUrl)
        return try {
            if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
            if (c.contentLengthLong > MAX_TEXT_BYTES) error("Text response is too large")
            c.inputStream.bufferedReader(Charsets.UTF_8).use { reader ->
                val chars = reader.readText()
                require(chars.toByteArray(Charsets.UTF_8).size.toLong() <= MAX_TEXT_BYTES) {
                    "Text response is too large"
                }
                chars
            }
        } finally {
            c.disconnect()
        }
    }

    private fun download(rawUrl: String, target: File, maxBytes: Long) {
        val c = open(rawUrl)
        try {
            if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
            val declared = c.contentLengthLong
            if (declared > maxBytes) error("Download exceeds safety limit")
            c.inputStream.use { input ->
                FileOutputStream(target, false).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    var total = 0L
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        total += n
                        if (total > maxBytes) error("Download exceeds safety limit")
                        output.write(buffer, 0, n)
                    }
                    output.fd.sync()
                    require(total > 0L) { "Downloaded file is empty" }
                }
            }
        } finally {
            c.disconnect()
        }
    }

    private fun open(rawUrl: String): HttpURLConnection {
        var current = URL(rawUrl)
        repeat(MAX_REDIRECTS + 1) { attempt ->
            requireTrustedUrl(current)
            val connection = (current.openConnection() as HttpURLConnection).apply {
                connectTimeout = 20_000
                readTimeout = 60_000
                instanceFollowRedirects = false
                requestMethod = "GET"
                setRequestProperty("User-Agent", "Droid-Launcher/${Build.VERSION.SDK_INT}")
                setRequestProperty("Accept", "application/json, application/octet-stream, */*")
            }
            val code = connection.responseCode
            if (code !in 300..399) return connection
            val location = connection.getHeaderField("Location")
            connection.disconnect()
            if (location.isNullOrBlank()) error("Redirect has no Location header")
            if (attempt >= MAX_REDIRECTS) error("Too many redirects")
            current = URI(current.toString()).resolve(location).toURL()
        }
        error("Redirect resolution failed")
    }

    private fun requireTrustedUrl(url: URL) {
        require(url.protocol.equals("https", true)) { "HTTPS required" }
        val host = url.host.lowercase()
        require(
            host == "api.github.com" ||
                host == "github.com" ||
                host == "objects.githubusercontent.com" ||
                host.endsWith(".githubusercontent.com")
        ) { "Untrusted updater host" }
    }

    private fun isGithubDownloadUrl(rawUrl: String): Boolean = try {
        val url = URL(rawUrl)
        url.protocol.equals("https", true) && when (url.host.lowercase()) {
            "github.com", "objects.githubusercontent.com" -> true
            else -> url.host.lowercase().endsWith(".githubusercontent.com")
        }
    } catch (_: Throwable) {
        false
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buffer)
                if (n < 0) break
                digest.update(buffer, 0, n)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun sanitize(value: String): String =
        value.replace(Regex("[^A-Za-z0-9._-]"), "_").take(80).ifBlank { "latest" }
}
