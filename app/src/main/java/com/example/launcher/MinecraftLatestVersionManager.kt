package com.example.launcher

import android.content.Context
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/** Resolves Mojang's authoritative latest release without hard-coding a version. */
object MinecraftLatestVersionManager {
    private const val MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
    private const val PREFS = "droid_launcher"
    private const val PREF_LATEST = "latest_minecraft_release"
    private const val TIMEOUT = 20_000
    private val executor = Executors.newSingleThreadExecutor()
    private val mainHandler = Handler(Looper.getMainLooper())

    data class Latest(val id: String, val url: String)

    fun getCached(context: Context): String? =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(PREF_LATEST, null)

    fun refresh(context: Context, onResult: (Latest?) -> Unit) {
        executor.execute {
            val latest = try { fetch() } catch (_: Throwable) { null }
            if (latest != null) {
                context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .edit().putString(PREF_LATEST, latest.id).apply()
            }
            mainHandler.post { onResult(latest) }
        }
    }

    private fun fetch(): Latest {
        val conn = openHttps(MANIFEST_URL)
        try {
            if (conn.responseCode !in 200..299) throw IOException("HTTP ${conn.responseCode}")
            val json = JSONObject(conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
            val latest = json.optJSONObject("latest") ?: throw IOException("No latest release")
            val id = latest.optString("release").trim()
            require(id.isNotBlank()) { "Latest release id is empty" }
            val versions = json.optJSONArray("versions") ?: throw IOException("No version list")
            for (i in 0 until versions.length()) {
                val v = versions.optJSONObject(i) ?: continue
                if (v.optString("id") == id) {
                    val url = v.optString("url").trim()
                    require(isTrustedMojangUrl(url)) { "Refusing untrusted Minecraft metadata URL" }
                    return Latest(id, url)
                }
            }
            throw IOException("Latest release metadata entry not found")
        } finally {
            conn.disconnect()
        }
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
