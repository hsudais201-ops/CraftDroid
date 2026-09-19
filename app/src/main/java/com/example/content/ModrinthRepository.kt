package com.example.content

import android.content.Context
import com.example.core.LauncherContainer
import com.example.launcher.MinecraftContentManager
import com.example.launcher.MinecraftModpackManager
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.URL
import java.security.MessageDigest

class ModrinthRepository(private val context: Context) {
    private val client = LauncherContainer.get(context).okHttpClient
    private val base = "https://api.modrinth.com/v2"

    suspend fun search(
        type: ContentType,
        query: String,
        gameVersion: String?,
        category: String?,
        offset: Int,
        limit: Int = 20
    ): ContentPage {
        if (type == ContentType.WORLD) return localWorlds(offset, limit)

        val facets = mutableListOf(JSONArray().put("project_type:" + type.projectType))
        if (!gameVersion.isNullOrBlank()) facets += JSONArray().put("versions:" + gameVersion)
        if (!category.isNullOrBlank()) facets += JSONArray().put("categories:" + category)
        val url = "$base/search".toHttpUrl().newBuilder()
            .addQueryParameter("query", query)
            .addQueryParameter("index", "downloads")
            .addQueryParameter("offset", offset.toString())
            .addQueryParameter("limit", limit.toString())
            .addQueryParameter("facets", JSONArray().apply { facets.forEach { put(it) } }.toString())
            .build()

        val request = Request.Builder().url(url).header("User-Agent", "DroidLauncher/2.4").build()
        val json = client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Modrinth returned HTTP ${response.code}")
            response.body?.string().orEmpty()
        }
        val root = JSONObject(json)
        val hits = root.optJSONArray("hits") ?: JSONArray()
        val items = buildList {
            for (i in 0 until hits.length()) {
                val item = hits.optJSONObject(i) ?: continue
                add(ContentItem(
                    id = item.optString("project_id"),
                    type = type,
                    name = item.optString("title").ifBlank { item.optString("slug") },
                    description = item.optString("description"),
                    iconUrl = item.optString("icon_url").ifBlank { null },
                    versions = jsonStringArray(item, "versions"),
                    loaders = jsonStringArray(item, "categories"),
                    categories = jsonStringArray(item, "categories"),
                    downloads = item.optLong("downloads", 0L)
                ))
            }
        }
        return ContentPage(items, offset, items.size == limit)
    }

    suspend fun install(item: ContentItem, gameVersion: String): File {
        require(!item.isLocal) { "Item is already installed locally" }

        val selected = selectCompatibleVersion(item, gameVersion)
            ?: error("No compatible " + item.type.title + " version found for Minecraft " + gameVersion)
        val selectedId = selected.optString("id").ifBlank { error("Modrinth returned a version without an id") }
        installVersionRecursive(item.type, selectedId, gameVersion, item.loaders, linkedSetOf())
        return File(context.cacheDir, "modrinth-install-complete-" + item.id)
    }

    private fun selectCompatibleVersion(item: ContentItem, gameVersion: String): JSONObject? {
        val url = "$base/project/" + item.id + "/version".toHttpUrl().newBuilder()
            .addQueryParameter("game_versions", JSONArray().put(gameVersion).toString())
            .addQueryParameter("limit", "50")
            .addQueryParameter("featured", "true")
            .build()
        val request = Request.Builder().url(url).header("User-Agent", "DroidLauncher/2.4").build()
        val versions = client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Could not load versions for " + item.name + " (HTTP " + response.code + ")")
            JSONArray(response.body?.string().orEmpty())
        }
        val preferredLoaders = item.loaders.filter {
            it.lowercase() in setOf("fabric", "forge", "neoforge", "quilt", "liteloader")
        }
        for (i in 0 until versions.length()) {
            val v = versions.optJSONObject(i) ?: continue
            val files = v.optJSONArray("files") ?: continue
            if (files.length() == 0) continue
            val loaders = jsonStringArray(v, "loaders")
            if (preferredLoaders.isNotEmpty() && loaders.none { it in preferredLoaders }) continue
            return v
        }
        return null
    }

    private fun installVersionRecursive(
        type: ContentType,
        versionId: String,
        gameVersion: String,
        preferredLoaders: List<String>,
        visited: MutableSet<String>
    ) {
        if (!visited.add(versionId)) return
        val version = fetchVersion(versionId)
        val files = version.optJSONArray("files") ?: JSONArray()
        val primary = (0 until files.length())
            .mapNotNull { files.optJSONObject(it) }
            .firstOrNull { it.optBoolean("primary") }
            ?: files.optJSONObject(0)
            ?: error("No downloadable file in Modrinth version " + versionId)

        val url = primary.optString("url")
        require(url.startsWith("https://")) { "Untrusted Modrinth download URL" }
        val tmp = File(context.cacheDir, "mr-" + System.nanoTime() + "-" + primary.optString("filename"))
        downloadVerified(url, tmp, primary.optLong("size", -1), primary.optJSONObject("hashes")?.optString("sha1"))
        try {
            if (type == ContentType.MODPACK) {
                MinecraftModpackManager.install(context, tmp)
            } else {
                MinecraftContentManager.importFile(context, type.kind, tmp, primary.optString("filename"))
            }
        } finally {
            tmp.delete()
        }

        val dependencies = version.optJSONArray("dependencies") ?: JSONArray()
        for (i in 0 until dependencies.length()) {
            val dep = dependencies.optJSONObject(i) ?: continue
            if (!dep.optString("dependency_type").equals("required", true)) continue
            val depVersionId = dep.optString("version_id").ifBlank { null }
            if (depVersionId != null) {
                installVersionRecursive(type, depVersionId, gameVersion, preferredLoaders, visited)
            } else {
                val projectId = dep.optString("project_id").ifBlank { null } ?: continue
                val depItem = ContentItem(
                    id = projectId,
                    type = ContentType.MOD,
                    name = projectId,
                    description = "",
                    iconUrl = null,
                    versions = listOf(gameVersion),
                    loaders = preferredLoaders,
                    categories = emptyList(),
                    downloads = 0L
                )
                val selectedDep = selectCompatibleVersion(depItem, gameVersion)
                    ?: error("Required dependency " + projectId + " has no compatible version for " + gameVersion)
                val depId = selectedDep.optString("id").ifBlank { error("Dependency " + projectId + " has no version id") }
                installVersionRecursive(ContentType.MOD, depId, gameVersion, preferredLoaders, visited)
            }
        }
    }

    private fun fetchVersion(versionId: String): JSONObject {
        val request = Request.Builder()
            .url(base + "/version/" + versionId)
            .header("User-Agent", "DroidLauncher/2.4")
            .build()
        return client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("Modrinth version lookup failed (HTTP " + response.code + ")")
            JSONObject(response.body?.string().orEmpty())
        }
    }

    private fun localWorlds(offset: Int, limit: Int): ContentPage {
        val files = MinecraftContentManager.list(context, MinecraftContentManager.Kind.WORLD)
        val page = files.drop(offset).take(limit).map { file ->
            ContentItem(
                id = file.absolutePath,
                type = ContentType.WORLD,
                name = file.name,
                description = "Local world",
                iconUrl = null,
                versions = emptyList(),
                loaders = emptyList(),
                categories = listOf("local"),
                downloads = 0L,
                isLocal = true,
                localFileName = file.name
            )
        }
        return ContentPage(page, offset, offset + page.size < files.size)
    }

    private fun jsonStringArray(obj: JSONObject, key: String): List<String> {
        val array = obj.optJSONArray(key) ?: return emptyList()
        return List(array.length()) { array.optString(it) }.filter { it.isNotBlank() }
    }

    private fun downloadVerified(url: String, target: File, expectedSize: Long, expectedSha1: String?) {
        val connection = URL(url).openConnection().apply {
            connectTimeout = 15_000
            readTimeout = 45_000
        }
        val digest = MessageDigest.getInstance("SHA-1")
        var count = 0L
        connection.getInputStream().use { input ->
            FileOutputStream(target).use { output ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    count += read
                    digest.update(buffer, 0, read)
                    output.write(buffer, 0, read)
                }
                output.fd.sync()
            }
        }
        require(expectedSize <= 0L || count == expectedSize) { "Download size verification failed" }
        if (!expectedSha1.isNullOrBlank()) {
            val actual = digest.digest().joinToString("") { "%02x".format(it) }
            require(actual.equals(expectedSha1, ignoreCase = true)) { "Download hash verification failed" }
        }
    }
}
