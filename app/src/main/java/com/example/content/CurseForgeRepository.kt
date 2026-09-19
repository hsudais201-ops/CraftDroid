package com.example.content

import android.content.Context
import android.net.Uri
import com.example.launcher.MinecraftContentManager
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.net.URL
import java.security.MessageDigest

/**
 * Secure CurseForge integration boundary.
 *
 * The Android app never stores a CurseForge API key. A user-owned HTTPS proxy
 * forwards requests to api.curseforge.com using the server-side key.
 */
class CurseForgeRepository(
    private val context: Context,
    private val client: OkHttpClient,
    private val proxyBaseUrl: String
) {
    fun isConfigured(): Boolean = proxyBaseUrl.trim().startsWith("https://")

    suspend fun search(
        type: ContentType,
        query: String,
        gameVersion: String?,
        loader: String?,
        categoryId: Int?,
        offset: Int,
        limit: Int = 20
    ): ContentPage {
        require(isConfigured()) {
            "CurseForge source is not configured. Set a HTTPS CurseForge proxy URL."
        }
        val classId = when (type) {
            ContentType.MOD -> 6
            ContentType.MODPACK -> 4471
            ContentType.RESOURCE_PACK -> 12
            ContentType.SHADER -> 6552
            ContentType.WORLD -> 17
        }
        val url = Uri.parse(proxyBaseUrl.trimEnd('/') + "/search").buildUpon()
            .appendQueryParameter("query", query)
            .appendQueryParameter("gameVersion", gameVersion.orEmpty())
            .appendQueryParameter("loader", loader.orEmpty())
            .appendQueryParameter("classId", classId.toString())
            .appendQueryParameter("categoryId", categoryId?.toString().orEmpty())
            .appendQueryParameter("index", offset.toString())
            .appendQueryParameter("pageSize", limit.toString())
            .build().toString()

        val root = client.newCall(
            Request.Builder().url(url)
                .header("User-Agent", "DroidLauncher/2.4")
                .header("Accept", "application/json")
                .build()
        ).execute().use { response ->
            if (!response.isSuccessful) error("CurseForge proxy returned HTTP " + response.code)
            JSONObject(response.body?.string().orEmpty())
        }

        val data = root.optJSONArray("data") ?: JSONArray()
        val items = buildList {
            for (i in 0 until data.length()) {
                val item = data.optJSONObject(i) ?: continue
                val categories = item.optJSONArray("categories") ?: JSONArray()
                val categoryNames = buildList {
                    for (j in 0 until categories.length()) {
                        categories.optJSONObject(j)?.optString("name")
                            ?.takeIf { it.isNotBlank() }?.let(::add)
                    }
                }
                add(
                    ContentItem(
                        id = item.optLong("id").toString(),
                        type = type,
                        name = item.optString("name").ifBlank { item.optString("slug") },
                        description = item.optString("summary"),
                        iconUrl = item.optJSONObject("logo")?.optString("url")?.ifBlank { null },
                        versions = jsonStringArray(item, "gameVersions"),
                        loaders = loader?.let { listOf(it) } ?: emptyList(),
                        categories = categoryNames,
                        downloads = item.optLong("downloadCount", 0L)
                    )
                )
            }
        }
        return ContentPage(items, offset, items.size == limit)
    }

    private fun fileInfo(modId: Long, fileId: Long, gameVersion: String): JSONObject {
        val url = Uri.parse(
            proxyBaseUrl.trimEnd('/') + "/file/" + modId + "/" + fileId
        ).buildUpon()
            .appendQueryParameter("gameVersion", gameVersion)
            .build().toString()

        return client.newCall(
            Request.Builder().url(url)
                .header("User-Agent", "DroidLauncher/2.4")
                .build()
        ).execute().use { response ->
            if (!response.isSuccessful) error("CurseForge file lookup failed (HTTP " + response.code + ")")
            JSONObject(response.body?.string().orEmpty())
        }
    }

    suspend fun install(item: ContentItem, gameVersion: String): File {
        require(isConfigured()) {
            "CurseForge source is not configured. Set a HTTPS CurseForge proxy URL."
        }

        val parts = item.id.split('/', limit = 2)
        val modId = parts.firstOrNull()?.toLongOrNull()
            ?: error("Invalid CurseForge project id: " + item.id)
        val fileId = if (parts.size == 2) {
            parts[1].toLongOrNull()
        } else {
            null
        }

        val info = if (fileId != null) {
            fileInfo(modId, fileId, gameVersion)
        } else {
            throw IllegalStateException("CurseForge item requires a resolved file id before installation")
        }

        val downloadUrl = info.optString("downloadUrl")
        if (!downloadUrl.startsWith("https://")) {
            val pageUrl = info.optString("websiteUrl")
            throw IllegalStateException(
                if (pageUrl.isNotBlank()) {
                    "CurseForge requires a third-party download restriction. Open: " + pageUrl
                } else {
                    "CurseForge did not provide a direct download for " + item.name
                }
            )
        }

        val target = File(
            context.cacheDir,
            "curseforge-" + System.nanoTime() + "-" + info.optString("fileName", "download.bin")
        )
        downloadVerified(
            downloadUrl,
            target,
            info.optLong("fileLength", -1L),
            info.optString("sha1").ifBlank { null }
        )

        return try {
            when (item.type) {
                ContentType.MOD, ContentType.SHADER, ContentType.RESOURCE_PACK ->
                    MinecraftContentManager.importFile(
                        context,
                        item.type.kind,
                        target,
                        info.optString("fileName", target.name)
                    )
                ContentType.MODPACK ->
                    installCurseForgeModpack(target)
                ContentType.WORLD ->
                    MinecraftContentManager.importArchive(
                        context,
                        MinecraftContentManager.Kind.WORLD,
                        target
                    )
            }
        } finally {
            target.delete()
        }
    }

    private fun installCurseForgeModpack(archive: File): File {
        java.util.zip.ZipFile(archive).use { zip ->
            val manifestEntry = zip.getEntry("manifest.json")
                ?: error("CurseForge modpack is missing manifest.json")
            val manifest = JSONObject(
                zip.getInputStream(manifestEntry).bufferedReader().use { it.readText() }
            )
            val name = manifest.optString("name").ifBlank { archive.nameWithoutExtension }
                .replace(Regex("[^A-Za-z0-9._ -]"), "_")
            val root = File(
                com.example.filesystem.MinecraftFileSystem(context).rootDir,
                "modpacks/curseforge/" + name
            ).apply { mkdirs() }
            val base = root.canonicalFile

            zip.entries().asSequence()
                .filter { it.name.startsWith("overrides/") }
                .forEach { entry ->
                    val relative = entry.name.removePrefix("overrides/")
                    if (relative.isBlank()) return@forEach
                    val target = File(root, relative).canonicalFile
                    require(
                        target.path == base.path ||
                            target.path.startsWith(base.path + File.separator)
                    ) { "Unsafe CurseForge override path" }

                    if (entry.isDirectory) {
                        target.mkdirs()
                    } else {
                        target.parentFile?.mkdirs()
                        zip.getInputStream(entry).use { input ->
                            FileOutputStream(target).use { output -> input.copyTo(output) }
                        }
                    }
                }

            File(root, "manifest.json").writeText(manifest.toString(2))
            archive.copyTo(File(root, "pack.zip"), overwrite = true)
            return root
        }
    }

    private fun jsonStringArray(obj: JSONObject, key: String): List<String> {
        val a = obj.optJSONArray(key) ?: return emptyList()
        return List(a.length()) { a.optString(it) }.filter { it.isNotBlank() }
    }

    private fun downloadVerified(
        url: String,
        target: File,
        expectedSize: Long,
        expectedSha1: String?
    ) {
        val connection = URL(url).openConnection().apply {
            connectTimeout = 15_000
            readTimeout = 45_000
        }
        val digest = MessageDigest.getInstance("SHA-1")
        var count = 0L
        target.parentFile?.mkdirs()
        connection.getInputStream().use { input ->
            FileOutputStream(target).use { output ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val read = input.read(buffer)
                    if (read < 0) break
                    output.write(buffer, 0, read)
                    digest.update(buffer, 0, read)
                    count += read
                }
                output.fd.sync()
            }
        }
        require(expectedSize <= 0L || count == expectedSize) {
            "CurseForge size verification failed"
        }
        if (!expectedSha1.isNullOrBlank()) {
            val actual = digest.digest().joinToString("") { "%02x".format(it) }
            require(actual.equals(expectedSha1, ignoreCase = true)) {
                "CurseForge SHA-1 verification failed"
            }
        }
    }
}
