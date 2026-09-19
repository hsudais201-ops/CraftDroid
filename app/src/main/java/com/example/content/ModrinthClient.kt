package com.example.content

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.delay
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder
import java.util.concurrent.ConcurrentHashMap

data class ContentProject(
    val id: String,
    val slug: String,
    val title: String,
    val projectType: String,
    val description: String?,
    val iconUrl: String?,
    val pageUrl: String
)

data class ContentDependency(val projectId: String?, val versionId: String?, val dependencyType: String)
data class ContentFile(val url: String, val fileName: String, val primary: Boolean, val sha1: String?, val size: Long)

data class ContentVersion(
    val id: String,
    val projectId: String,
    val name: String,
    val gameVersions: List<String>,
    val loaders: List<String>,
    val dependencies: List<ContentDependency>,
    val files: List<ContentFile>,
    val projectType: String
)

class ModrinthClient(private val http: OkHttpClient) {
    private val responseCache = ConcurrentHashMap<String, Pair<Long, String>>()
    private val cacheTtlMs = 5 * 60 * 1000L
    companion object {
        const val BASE_URL = "https://api.modrinth.com/v2"
        private val ALLOWED_TYPES = setOf("mod", "modpack", "resourcepack", "shader", "datapack", "plugin")
    }

    suspend fun search(query: String, gameVersion: String? = null, loader: String? = null, projectType: String? = null): List<ContentProject> =
        withContext(Dispatchers.IO) {
            if (projectType != null && projectType !in ALLOWED_TYPES) {
                throw IllegalArgumentException("Modrinth does not expose " + projectType + " as a project type; Worlds use CurseForge.")
            }
            val facets = JSONArray()
            fun facet(v: String) { facets.put(JSONArray().put(v)) }
            projectType?.let { facet("project_type:" + it) }
            gameVersion?.let { facet("versions:" + it) }
            loader?.takeIf { it.isNotBlank() }?.let { facet("categories:" + it) }
            val url = BASE_URL + "/search?query=" + enc(query) + "&facets=" + enc(facets.toString()) + "&limit=20"
            val hits = getObject(url).optJSONArray("hits") ?: JSONArray()
            buildList {
                for (i in 0 until hits.length()) {
                    val item = hits.optJSONObject(i) ?: continue
                    val type = item.optString("project_type")
                    val slug = item.optString("slug")
                    add(ContentProject(
                        id = item.optString("project_id"),
                        slug = slug,
                        title = item.optString("title"),
                        projectType = type,
                        description = item.optString("description").takeIf { it.isNotBlank() },
                        iconUrl = item.optString("icon_url").takeIf { it.isNotBlank() },
                        pageUrl = "https://modrinth.com/" + type + "/" + slug
                    ))
                }
            }
        }

    suspend fun getVersions(projectId: String, gameVersion: String? = null, loader: String? = null): List<ContentVersion> =
        withContext(Dispatchers.IO) {
            val params = mutableListOf<String>()
            gameVersion?.let { params += "game_versions=" + enc(JSONArray().put(it).toString()) }
            loader?.let { params += "loaders=" + enc(JSONArray().put(it).toString()) }
            val query = if (params.isEmpty()) "" else "?" + params.joinToString("&")
            val arr = getArray(BASE_URL + "/project/" + enc(projectId) + "/version" + query)
            buildList { for (i in 0 until arr.length()) add(parseVersion(arr.getJSONObject(i))) }
        }

    suspend fun getVersion(versionId: String): ContentVersion =
        withContext(Dispatchers.IO) { parseVersion(getObject(BASE_URL + "/version/" + enc(versionId))) }

    suspend fun resolveBestVersion(projectId: String, gameVersion: String, loader: String?): ContentVersion {
        return getVersions(projectId, gameVersion, loader).firstOrNull {
            it.gameVersions.contains(gameVersion) && (loader == null || it.loaders.contains(loader))
        } ?: throw IOException(
            "Modrinth has no compatible version for project=" + projectId +
                " Minecraft=" + gameVersion + " loader=" + (loader ?: "any")
        )
    }

    suspend fun resolveRequiredDependencies(root: ContentVersion, gameVersion: String, loader: String?, maxNodes: Int = 128): List<ContentVersion> =
        withContext(Dispatchers.IO) {
            val resolved = LinkedHashMap<String, ContentVersion>()
            val queue = ArrayDeque<ContentDependency>()
            root.dependencies.filter { it.dependencyType.equals("required", true) }.forEach(queue::addLast)

            while (queue.isNotEmpty()) {
                if (resolved.size >= maxNodes) throw IOException("Modrinth dependency graph exceeded " + maxNodes + " nodes")
                val dep = queue.removeFirst()
                val key = dep.versionId ?: dep.projectId ?: continue
                if (resolved.containsKey(key)) continue
                val version = dep.versionId?.let { getVersion(it) }
                    ?: resolveBestVersion(dep.projectId!!, gameVersion, loader)
                resolved[key] = version
                version.dependencies.filter { it.dependencyType.equals("required", true) }.forEach(queue::addLast)
            }
            resolved.values.toList()
        }

    private fun parseVersion(root: JSONObject): ContentVersion {
        val files = root.optJSONArray("files") ?: JSONArray()
        val deps = root.optJSONArray("dependencies") ?: JSONArray()
        return ContentVersion(
            id = root.optString("id"),
            projectId = root.optString("project_id"),
            name = root.optString("name"),
            gameVersions = strings(root.optJSONArray("game_versions")),
            loaders = strings(root.optJSONArray("loaders")),
            dependencies = buildList {
                for (i in 0 until deps.length()) {
                    val d = deps.optJSONObject(i) ?: continue
                    add(ContentDependency(
                        d.optString("project_id").takeIf { it.isNotBlank() },
                        d.optString("version_id").takeIf { it.isNotBlank() },
                        d.optString("dependency_type", "required")
                    ))
                }
            },
            files = buildList {
                for (i in 0 until files.length()) {
                    val f = files.optJSONObject(i) ?: continue
                    add(ContentFile(
                        f.optString("url"),
                        f.optString("filename"),
                        f.optBoolean("primary", false),
                        f.optJSONObject("hashes")?.optString("sha1")?.takeIf { it.isNotBlank() },
                        f.optLong("size", 0L)
                    ))
                }
            },
            projectType = root.optString("project_type")
        )
    }

    private fun strings(a: JSONArray?): List<String> =
        if (a == null) emptyList() else buildList { for (i in 0 until a.length()) add(a.optString(i)) }

    private suspend fun getObject(url: String): JSONObject {
        val cached = responseCache[url]?.takeIf { System.currentTimeMillis() - it.first < cacheTtlMs }?.second
        if (cached != null) return JSONObject(cached)
        val body = requestBody(url)
        responseCache[url] = System.currentTimeMillis() to body
        return JSONObject(body)
    }

    private suspend fun requestBody(url: String): String {
        for (attempt in 0 until 3) {
            val request = Request.Builder().url(url).header("Accept", "application/json")
                .header("User-Agent", "CraftDroid-Launcher/2.5").build()
            val response = http.newCall(request).execute()
            var retry = false
            var result: String? = null
            response.use {
                if (it.code == 429) {
                    val retryAfter = it.header("Retry-After")?.toLongOrNull()?.coerceIn(1L, 30L) ?: ((attempt + 1L) * 2L)
                    delay(retryAfter * 1000L)
                    retry = true
                } else {
                    if (!it.isSuccessful) throw IOException("Modrinth HTTP " + it.code + " for " + url)
                    result = it.body?.string() ?: throw IOException("Modrinth returned an empty response")
                }
            }
            if (retry) continue
            return result!!
        }
        throw IOException("Modrinth rate limit persisted after 3 attempts")
    }
    private suspend fun getArray(url: String): JSONArray {
        val cached = responseCache[url]?.takeIf { System.currentTimeMillis() - it.first < cacheTtlMs }?.second
        if (cached != null) return JSONArray(cached)
        val body = requestBody(url)
        responseCache[url] = System.currentTimeMillis() to body
        return JSONArray(body)
    }

    private fun enc(v: String): String = URLEncoder.encode(v, "UTF-8")
}
