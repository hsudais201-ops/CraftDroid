package com.example.server

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID

class ServerStore(context: Context) {
    private val prefs = context.getSharedPreferences("servers", Context.MODE_PRIVATE)

    fun load(): List<SavedServer> {
        val raw = prefs.getString("items", "[]").orEmpty()
        val json = runCatching { JSONArray(raw) }.getOrElse { JSONArray() }
        return buildList {
            for (i in 0 until json.length()) {
                val o = json.optJSONObject(i) ?: continue
                val host = o.optString("host").trim()
                val port = o.optInt("port", 25565).coerceIn(1, 65535)
                if (host.isNotBlank()) {
                    add(SavedServer(
                        id = o.optString("id").ifBlank { UUID.randomUUID().toString() },
                        name = o.optString("name").ifBlank { host },
                        host = host,
                        port = port
                    ))
                }
            }
        }
    }

    fun save(items: List<SavedServer>) {
        val json = JSONArray().apply {
            items.forEach { item ->
                put(JSONObject()
                    .put("id", item.id)
                    .put("name", item.name)
                    .put("host", item.host)
                    .put("port", item.port))
            }
        }
        prefs.edit().putString("items", json.toString()).apply()
    }
}
