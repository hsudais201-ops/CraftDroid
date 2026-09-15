package com.example.launcher

import android.content.Context
import android.os.Build
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.Executors

/**
 * Checks the public CraftDroid GitHub Releases API for a newer Droid Launcher
 * APK. The updater never installs an unverified APK: when a .sha256 release
 * asset exists, the downloaded APK must match it before the file is returned.
 */
object DroidLauncherUpdateManager {
    private const val API_URL = "https://api.github.com/repos/hsudais201-ops/CraftDroid/releases/latest"
    private const val PREFS = "droid_launcher_updates"
    private const val LAST_CHECK = "last_check_ms"
    private const val CHECK_INTERVAL_MS = 6 * 60 * 60 * 1000L
    private val executor = Executors.newSingleThreadExecutor()

    data class Release(val tag: String, val apkUrl: String, val sha256Url: String?)

    fun shouldCheck(context: Context): Boolean =
        System.currentTimeMillis() - context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getLong(LAST_CHECK, 0L) >= CHECK_INTERVAL_MS

    fun check(context: Context, onResult: (Release?) -> Unit) {
        executor.execute {
            val result = try { fetchLatest() } catch (_: Throwable) { null }
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                .putLong(LAST_CHECK, System.currentTimeMillis()).apply()
            onResult(result)
        }
    }

    fun downloadVerified(context: Context, release: Release): File {
        val updateDir = File(context.cacheDir, "launcher-updates")
        if (!updateDir.exists() && !updateDir.mkdirs()) throw IllegalStateException("Could not create update cache")
        val apk = File(updateDir, "droid-launcher-${sanitize(release.tag)}.apk")
        download(release.apkUrl, apk)
        val expected = release.sha256Url?.let { downloadText(it).trim().split(Regex("\\s+")).firstOrNull() }
        if (!expected.isNullOrBlank()) {
            val actual = sha256(apk)
            require(actual.equals(expected, ignoreCase = true)) { "Launcher update SHA-256 verification failed" }
        }
        require(apk.isFile && apk.length() > 0L) { "Downloaded launcher update is empty" }
        return apk
    }

    private fun fetchLatest(): Release? {
        val json = org.json.JSONObject(downloadText(API_URL))
        val tag = json.optString("tag_name").ifBlank { return null }
        val assets = json.optJSONArray("assets") ?: return null
        var apk: String? = null
        var sha: String? = null
        for (i in 0 until assets.length()) {
            val a = assets.optJSONObject(i) ?: continue
            val name = a.optString("name")
            val url = a.optString("browser_download_url")
            if (name.endsWith(".apk", true) && url.startsWith("https://")) apk = url
            if (name.endsWith(".sha256", true) && url.startsWith("https://")) sha = url
        }
        return apk?.let { Release(tag, it, sha) }
    }

    private fun downloadText(rawUrl: String): String {
        val c = open(rawUrl)
        return try {
            if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
            c.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally { c.disconnect() }
    }

    private fun download(rawUrl: String, target: File) {
        val c = open(rawUrl)
        try {
            if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
            c.inputStream.use { input ->
                FileOutputStream(target, false).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        output.write(buffer, 0, n)
                    }
                    output.fd.sync()
                }
            }
        } finally { c.disconnect() }
    }

    private fun open(rawUrl: String): HttpURLConnection =
        (URL(rawUrl).openConnection() as HttpURLConnection).apply {
            require(URL(rawUrl).protocol == "https") { "HTTPS required" }
            connectTimeout = 20_000
            readTimeout = 60_000
            instanceFollowRedirects = true
            requestMethod = "GET"
            setRequestProperty("User-Agent", "Droid-Launcher/${Build.VERSION.SDK_INT}")
            setRequestProperty("Accept", "application/json, application/octet-stream, */*")
        }

    private fun sha256(file: File): String {
        val d = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buffer)
                if (n < 0) break
                d.update(buffer, 0, n)
            }
        }
        return d.digest().joinToString("") { "%02x".format(it) }
    }

    private fun sanitize(value: String): String = value.replace(Regex("[^A-Za-z0-9._-]"), "_").take(80)
}
