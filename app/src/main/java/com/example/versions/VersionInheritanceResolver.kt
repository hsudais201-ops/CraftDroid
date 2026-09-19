package com.example.versions

import android.util.Log
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/** Resolves Minecraft version.json inheritance before parsing/launching.
 *
 * Mojang/mod-loader profiles may use inheritsFrom. The child profile can add or
 * override libraries, arguments and metadata while relying on the parent for
 * the remaining launch data. This resolver produces one normalized manifest.
 */
class VersionInheritanceResolver(
    private val fileSystem: MinecraftFileSystem,
    private val client: OkHttpClient
) {
    suspend fun resolve(versionId: String, rawJson: String): String = withContext(Dispatchers.IO) {
        resolveRecursive(versionId, JSONObject(rawJson), linkedSetOf()).toString()
    }

    private fun resolveRecursive(id: String, child: JSONObject, visiting: MutableSet<String>): JSONObject {
        val parentId = child.optString("inheritsFrom", "").trim()
        if (parentId.isEmpty()) return child
        if (!visiting.add(id)) throw IllegalStateException("Circular Minecraft version inheritance: ${visiting.joinToString(" -> ")}")

        val parentRaw = loadParentJson(parentId)
            ?: throw IllegalStateException("Minecraft version $id inherits from $parentId, but the parent manifest is unavailable")
        val parentResolved = resolveRecursive(parentId, JSONObject(parentRaw), visiting)
        val merged = merge(parentResolved, child)
        merged.put("id", id)
        merged.remove("inheritsFrom")
        visiting.remove(id)
        LauncherLogger.info("Resolved Minecraft version inheritance: $id <- $parentId")
        return merged
    }

    private fun loadParentJson(id: String): String? {
        val local = fileSystem.getVersionJsonFile(id)
        if (local.exists() && local.length() > 0) return local.readText()

        // Parent profiles are normally Mojang versions. Resolve them from the
        // official version manifest when they are not installed locally.
        return try {
            val manifestRequest = Request.Builder()
                .url("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
                .header("Accept", "application/json")
                .build()
            client.newCall(manifestRequest).execute().use { response ->
                if (!response.isSuccessful) return null
                val root = JSONObject(response.body?.string() ?: return null)
                val versions = root.optJSONArray("versions") ?: return null
                for (i in 0 until versions.length()) {
                    val entry = versions.getJSONObject(i)
                    if (entry.optString("id") == id) {
                        val url = entry.optString("url", "")
                        if (url.isBlank()) return null
                        val req = Request.Builder().url(url).header("Accept", "application/json").build()
                        client.newCall(req).execute().use { parentResponse ->
                            if (!parentResponse.isSuccessful) return null
                            return parentResponse.body?.string()
                        }
                    }
                }
                null
            }
        } catch (e: Exception) {
            LauncherLogger.warn("Could not fetch inherited parent $id: ${e.message}")
            null
        }
    }

    private fun merge(parent: JSONObject, child: JSONObject): JSONObject {
        val out = JSONObject(parent.toString())
        val childKeys = child.keys()
        while (childKeys.hasNext()) {
            val key = childKeys.next()
            when (key) {
                "libraries" -> out.put("libraries", mergeLibraries(parent.optJSONArray(key), child.optJSONArray(key)))
                "arguments" -> out.put("arguments", mergeArguments(parent.optJSONObject(key), child.optJSONObject(key)))
                "minecraftArguments" -> {
                    // A child using legacy arguments replaces the parent's legacy string.
                    out.put(key, child.optString(key))
                    out.remove("arguments")
                }
                "id", "inheritsFrom" -> { /* handled by caller */ }
                else -> out.put(key, child.get(key))
            }
        }
        return out
    }

    private fun mergeLibraries(parent: JSONArray?, child: JSONArray?): JSONArray {
        val ordered = LinkedHashMap<String, JSONObject>()
        fun add(array: JSONArray?) {
            if (array == null) return
            for (i in 0 until array.length()) {
                val value = array.opt(i)
                if (value is JSONObject) {
                    ordered[value.optString("name", "#${i}_${value.hashCode()}")] = JSONObject(value.toString())
                }
            }
        }
        add(parent)
        add(child) // child definition wins while preserving first-seen ordering
        return JSONArray().apply { ordered.values.forEach { put(it) } }
    }

    private fun mergeArguments(parent: JSONObject?, child: JSONObject?): JSONObject {
        if (parent == null && child == null) return JSONObject()
        val result = JSONObject()
        for (key in listOf("jvm", "game")) {
            val merged = JSONArray()
            append(parent?.optJSONArray(key), merged)
            append(child?.optJSONArray(key), merged)
            if (merged.length() > 0) result.put(key, merged)
        }
        // Preserve any uncommon argument arrays from either manifest.
        val keys = linkedSetOf<String>()
        parent?.keys()?.forEachRemaining { keys.add(it) }
        child?.keys()?.forEachRemaining { keys.add(it) }
        for (key in keys) if (!result.has(key)) {
            val source = child?.opt(key) ?: parent?.opt(key)
            if (source != null) result.put(key, source)
        }
        return result
    }

    private fun append(source: JSONArray?, target: JSONArray) {
        if (source == null) return
        for (i in 0 until source.length()) target.put(source.get(i))
    }
}
