package com.example.content

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder

data class CurseForgeSearchResult(
    val id: Long,
    val name: String,
    val slug: String,
    val summary: String,
    val pageUrl: String,
    val classId: Int?,
    val categoryIds: List<Int>,
    val available: Boolean,
    val allowDistribution: Boolean
)

data class CurseForgeFile(
    val id: Long,
    val modId: Long,
    val fileName: String,
    val displayName: String,
    val downloadUrl: String?,
    val fileLength: Long,
    val gameVersions: List<String>,
    val dependencies: List<Pair<Long, Long?>>,
    val pageUrl: String
)

class CurseForgeClient(private val http: OkHttpClient, private val proxyBaseUrl: String) {
    companion object { const val GAME_ID = 432 }

    private fun requireProxy() {
        if (proxyBaseUrl.isBlank()) {
            throw IllegalStateException("CurseForge is not configured. Set CURSEFORGE_PROXY_BASE_URL on your backend; never ship the API key in the APK.")
        }
    }

    suspend fun categories(): JSONArray = withContext(Dispatchers.IO) {
        requireProxy()
        getJson(proxyBaseUrl + "/v1/categories?gameId=" + GAME_ID).optJSONArray("data") ?: JSONArray()
    }

    suspend fun search(query: String = "", gameVersion: String? = null, loaderType: Int? = null, classId: Int? = null): List<CurseForgeSearchResult> =
        withContext(Dispatchers.IO) {
            requireProxy()
            val params = mutableListOf("gameId=" + GAME_ID, "pageSize=20")
            if (query.isNotBlank()) params += "searchFilter=" + enc(query)
            gameVersion?.let { params += "gameVersion=" + enc(it) }
            loaderType?.let { params += "modLoaderType=" + it }
            classId?.let { params += "classId=" + it }
            val data = getJson(proxyBaseUrl + "/v1/mods/search?" + params.joinToString("&")).optJSONArray("data") ?: JSONArray()
            buildList {
                for (i in 0 until data.length()) {
                    val item = data.optJSONObject(i) ?: continue
                    val links = item.optJSONObject("links")
                    add(CurseForgeSearchResult(
                        item.optLong("id"),
                        item.optString("name"),
                        item.optString("slug"),
                        item.optString("summary"),
                        links?.optString("websiteUrl") ?: "https://www.curseforge.com/",
                        item.optInt("classId", -1).takeIf { it >= 0 },
                        ints(item.optJSONArray("categories")),
                        item.optBoolean("isAvailable", true),
                        item.optBoolean("allowModDistribution", true)
                    ))
                }
            }
        }

    suspend fun getFile(modId: Long, fileId: Long): CurseForgeFile = withContext(Dispatchers.IO) {
        requireProxy()
        parseFile(getJson(proxyBaseUrl + "/v1/mods/" + modId + "/files/" + fileId).optJSONObject("data")
            ?: throw IOException("CurseForge returned no file metadata"))
    }

    suspend fun getProject(modId: Long): CurseForgeSearchResult = withContext(Dispatchers.IO) {
        requireProxy()
        val item = getJson(proxyBaseUrl + "/v1/mods/" + modId).optJSONObject("data")
            ?: throw IOException("CurseForge returned no project metadata")
        val links = item.optJSONObject("links")
        CurseForgeSearchResult(
            item.optLong("id"), item.optString("name"), item.optString("slug"), item.optString("summary"),
            links?.optString("websiteUrl") ?: "https://www.curseforge.com/",
            item.optInt("classId", -1).takeIf { it >= 0 },
            ints(item.optJSONArray("categories")),
            item.optBoolean("isAvailable", true),
            item.optBoolean("allowModDistribution", true)
        )
    }

    suspend fun resolveRequiredDependencies(root: CurseForgeFile, maxNodes: Int = 128): List<CurseForgeFile> =
        withContext(Dispatchers.IO) {
            val resolved = LinkedHashMap<String, CurseForgeFile>()
            val queue = ArrayDeque<Pair<Long, Long?>>()
            root.dependencies.forEach(queue::addLast)
            while (queue.isNotEmpty()) {
                if (resolved.size >= maxNodes) throw IOException("CurseForge dependency graph exceeded " + maxNodes + " nodes")
                val (modId, fileId) = queue.removeFirst()
                if (fileId == null) throw IOException("CurseForge dependency " + modId + " did not provide a compatible file id")
                val key = modId.toString() + ":" + fileId
                if (resolved.containsKey(key)) continue
                val file = getFile(modId, fileId)
                resolved[key] = file
                file.dependencies.forEach(queue::addLast)
            }
            resolved.values.toList()
        }

    suspend fun distributionUrl(modId: Long, fileId: Long): String {
        val project = getProject(modId)
        val file = getFile(modId, fileId)
        if (!project.available || !project.allowDistribution || file.downloadUrl.isNullOrBlank()) {
            throw CurseForgeDistributionDisabledException(
                project.pageUrl,
                "Third-party distribution is disabled for " + file.fileName
            )
        }
        return file.downloadUrl
    }

    private fun parseFile(item: JSONObject): CurseForgeFile {
        val links = item.optJSONObject("links")
        val deps = item.optJSONArray("dependencies") ?: JSONArray()
        val dependencies = buildList<Pair<Long, Long?>> {
            for (i in 0 until deps.length()) {
                val d = deps.optJSONObject(i) ?: continue
                if (d.optInt("relationType", -1) == 3 && d.optLong("modId") > 0) {
                    add(d.optLong("modId") to d.optLong("fileId", 0).takeIf { it > 0 })
                }
            }
        }
        return CurseForgeFile(
            item.optLong("id"), item.optLong("modId"), item.optString("fileName"),
            item.optString("displayName"), item.optString("downloadUrl").takeIf { it.isNotBlank() },
            item.optLong("fileLength", 0L), strings(item.optJSONArray("gameVersions")),
            dependencies, links?.optString("websiteUrl") ?: "https://www.curseforge.com/"
        )
    }

    private fun getJson(url: String): JSONObject {
        val r = Request.Builder().url(url).header("Accept", "application/json")
            .header("User-Agent", "CraftDroid-Launcher/2.5").build()
        http.newCall(r).execute().use { response ->
            if (!response.isSuccessful) throw IOException("CurseForge HTTP " + response.code + " for " + url)
            return JSONObject(response.body?.string() ?: throw IOException("CurseForge returned an empty response"))
        }
    }

    private fun strings(a: JSONArray?): List<String> =
        if (a == null) emptyList() else buildList { for (i in 0 until a.length()) add(a.optString(i)) }

    private fun ints(a: JSONArray?): List<Int> =
        if (a == null) emptyList() else buildList { for (i in 0 until a.length()) add(a.optInt(i)) }

    private fun enc(v: String): String = URLEncoder.encode(v, "UTF-8")
}

class CurseForgeDistributionDisabledException(val pageUrl: String, message: String) : IOException(message)
