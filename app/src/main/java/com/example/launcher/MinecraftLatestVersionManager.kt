package com.example.launcher

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/** Resolves Mojang's authoritative latest release without hard-coding a version. */
object MinecraftLatestVersionManager {
    private const val MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val PREFS = "droid_launcher"
    private const val PREF_LATEST = "latest_minecraft_release"
    private const val PREF_RELEASES = "minecraft_release_ids"
    private const val TIMEOUT = 20_000
    private const val MAX_MANIFEST_BYTES = 8L * 1024L * 1024L
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    data class Latest(val id: String, val url: String, val releaseIds: List<String> = emptyList())

    fun getCached(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(PREF_LATEST, null)

    fun getCachedChoices(context: Context): List<String> =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getString(PREF_RELEASES, null)
            ?.split('\n')
            ?.map { it.trim() }
            ?.filter { it.isNotBlank() }
            ?: emptyList()

    fun refresh(context: Context, onResult: (Latest?) -> Unit) {
        executor.execute {
            val latest = try { fetch() } catch (_: Throwable) { null }
            if (latest != null) {
                val editor = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
                    .putString(PREF_LATEST, latest.id)
                if (latest.releaseIds.isNotEmpty()) {
                    editor.putString(PREF_RELEASES, latest.releaseIds.joinToString("\n"))
                }
                editor.apply()
            }
            mainHandler.post { onResult(latest) }
        }
    }

    private fun fetch(): Latest {
        val conn = openHttps(MANIFEST_URL)
        try {
            if (conn.responseCode !in 200..299) throw IOException("HTTP ${conn.responseCode}")
            val json = JSONObject(readManifestText(conn))
            val latest = json.optJSONObject("latest") ?: throw IOException("No latest release")
            val id = latest.optString("release").trim()
            require(id.isNotBlank()) { "Latest release id is empty" }
            val versions = json.optJSONArray("versions") ?: throw IOException("No version list")
            val releaseIds = ArrayList<String>(versions.length())
            var latestUrl = ""
            for (i in 0 until versions.length()) {
                val v = versions.optJSONObject(i) ?: continue
                if (v.optString("type") == "release") {
                    val versionId = v.optString("id").trim()
                    if (versionId.isNotBlank()) releaseIds.add(versionId)
                }
                if (v.optString("id") == id) {
                    latestUrl = v.optString("url").trim()
                }
            }
            require(latestUrl.isNotBlank()) { "Latest release metadata entry not found" }
            require(isTrustedMojangUrl(latestUrl)) { "Refusing untrusted Minecraft metadata URL" }
            return Latest(id, latestUrl, releaseIds)
        } finally {
            conn.disconnect()
        }
    }

    private fun readManifestText(conn: HttpURLConnection): String {
        if (conn.contentLengthLong > MAX_MANIFEST_BYTES) {
            throw IOException("Mojang version manifest exceeds safety limit")
        }
        val output = ByteArrayOutputStream()
        val buffer = ByteArray(64 * 1024)
        conn.inputStream.use { input ->
            var total = 0L
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                if (count == 0) continue
                total += count
                if (total > MAX_MANIFEST_BYTES) {
                    throw IOException("Mojang version manifest exceeds safety limit")
                }
                output.write(buffer, 0, count)
            }
        }
        return output.toByteArray().toString(Charsets.UTF_8)
    }

    private fun openHttps(rawUrl: String): HttpURLConnection {
        val parsed = URL(rawUrl)
        require(parsed.protocol.equals("https", true)) { "HTTPS required" }
        require(parsed.host.equals("piston-meta.mojang.com", true)) { "Untrusted Mojang host" }
        return (parsed.openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = TIMEOUT
            readTimeout = TIMEOUT
            instanceFollowRedirects = false
            setRequestProperty("Accept", "application/json")
            setRequestProperty("User-Agent", "Droid-Launcher-Minecraft-Version-Resolver")
        }
    }

    private fun isTrustedMojangUrl(rawUrl: String): Boolean = try {
        val parsed = URL(rawUrl)
        parsed.protocol.equals("https", true) && parsed.host.equals("piston-meta.mojang.com", true)
    } catch (_: Throwable) {
        false
    }
}
