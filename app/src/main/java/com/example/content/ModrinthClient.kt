package com.example.content

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder

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

    private fun getObject(url: String): JSONObject {
        val r = Request.Builder().url(url).header("Accept", "application/json")
            .header("User-Agent", "CraftDroid-Launcher/2.5").build()
        http.newCall(r).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Modrinth HTTP " + response.code + " for " + url)
            return JSONObject(response.body?.string() ?: throw IOException("Modrinth returned an empty response"))
        }
    }

    private fun getArray(url: String): JSONArray {
        val r = Request.Builder().url(url).header("Accept", "application/json")
            .header("User-Agent", "CraftDroid-Launcher/2.5").build()
        http.newCall(r).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Modrinth HTTP " + response.code + " for " + url)
            return JSONArray(response.body?.string() ?: throw IOException("Modrinth returned an empty response"))
        }
    }

    private fun enc(v: String): String = URLEncoder.encode(v, "UTF-8")
}
