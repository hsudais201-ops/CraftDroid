package com.example.minecraft

import com.example.downloader.DownloadManager
import com.example.downloader.DownloadTask
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException

data class QuiltInstallResult(
    val success: Boolean,
    val profileId: String,
    val loaderVersion: String,
    val downloadedLibraries: Int,
    val error: String? = null
)

class QuiltLoaderInstaller(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager,
    private val okHttpClient: OkHttpClient
) {
    suspend fun install(
        minecraftVersion: String,
        loaderVersion: String
    ): QuiltInstallResult = withContext(Dispatchers.IO) {
        val url = "https://meta.quiltmc.org/v3/versions/loader/" +
            minecraftVersion + "/" + loaderVersion + "/profile/json"
        try {
            val vanillaJson = fileSystem.getVersionJsonFile(minecraftVersion)
            val vanillaJar = fileSystem.getVersionJarFile(minecraftVersion)
            if (!vanillaJson.exists() || !vanillaJar.exists()) {
                throw IOException("Minecraft " + minecraftVersion + " must be installed before Quilt")
            }

            val request = Request.Builder()
                .url(url)
                .header("User-Agent", "DroidLauncher/2.4")
                .header("Accept", "application/json")
                .build()
            val profileJson = okHttpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("Quilt Meta HTTP " + response.code)
                response.body?.string() ?: throw IOException("Empty Quilt profile response")
            }

            val root = JSONObject(profileJson)
            val profileId = root.optString("id").ifBlank {
                "quilt-loader-" + loaderVersion + "-" + minecraftVersion
            }
            val inheritsFrom = root.optString("inheritsFrom")
            if (inheritsFrom.isNotBlank() && inheritsFrom != minecraftVersion) {
                throw IOException("Quilt profile inherits from " + inheritsFrom + ", expected " + minecraftVersion)
            }
            val mainClass = root.optString("mainClass")
            if (mainClass.isBlank()) throw IOException("Quilt profile has no mainClass")

            val profileDir = fileSystem.getVersionDir(profileId)
            File(profileDir, profileId + ".json").writeText(profileJson)
            val profileJar = File(profileDir, profileId + ".jar")
            if (!profileJar.exists() || profileJar.length() != vanillaJar.length()) {
                vanillaJar.copyTo(profileJar, overwrite = true)
            }

            val sourceNatives = fileSystem.getNativesDir(minecraftVersion)
            val targetNatives = fileSystem.getNativesDir(profileId)
            if (sourceNatives.isDirectory) {
                targetNatives.mkdirs()
                sourceNatives.listFiles()?.forEach { source ->
                    if (source.isFile && source.name.endsWith(".so")) {
                        source.copyTo(File(targetNatives, source.name), overwrite = true)
                    }
                }
            }

            val libraries = root.optJSONArray("libraries") ?: JSONArray()
            val tasks = mutableListOf<DownloadTask>()
            for (i in 0 until libraries.length()) {
                val lib = libraries.optJSONObject(i) ?: continue
                val name = lib.optString("name")
                if (name.isBlank()) continue
                val artifact = lib.optJSONObject("downloads")?.optJSONObject("artifact")
                val path = artifact?.optString("path")?.takeIf { it.isNotBlank() } ?: mavenArtifactPath(name)
                val baseUrl = lib.optString("url", "https://maven.quiltmc.org/repository/release/")
                val normalizedBase = if (baseUrl.endsWith("/")) baseUrl else baseUrl + "/"
                tasks += DownloadTask(
                    url = artifact?.optString("url")?.takeIf { it.isNotBlank() } ?: normalizedBase + path,
                    destination = File(fileSystem.librariesDir, path),
                    expectedSha1 = artifact?.optString("sha1")?.takeIf { it.isNotBlank() }
                        ?: lib.optString("sha1", null).takeIf { !it.isNullOrBlank() },
                    size = artifact?.optLong("size", 0L) ?: lib.optLong("size", 0L),
                    name = name
                )
            }

            val uniqueTasks = tasks.distinctBy { it.destination.absolutePath }
            val ok = downloadManager.downloadQueue(uniqueTasks)
            if (!ok) throw IOException("One or more Quilt libraries failed to download")

            LauncherLogger.info("Installed Quilt profile " + profileId + " with " + uniqueTasks.size + " libraries")
            QuiltInstallResult(true, profileId, loaderVersion, uniqueTasks.size)
        } catch (e: Exception) {
            LauncherLogger.error("Quilt installation failed: " + e.message)
            QuiltInstallResult(
                false,
                "quilt-loader-" + loaderVersion + "-" + minecraftVersion,
                loaderVersion,
                0,
                e.message
            )
        }
    }

    private fun mavenArtifactPath(name: String): String {
        val parts = name.split(":")
        if (parts.size < 3) throw IOException("Invalid Maven coordinate: " + name)
        val group = parts[0].replace('.', '/')
        val artifact = parts[1]
        val versionExt = parts[2].split("@", limit = 2)
        val version = versionExt[0]
        val ext = if (versionExt.size == 2) versionExt[1] else "jar"
        val classifier = if (parts.size >= 4) "-" + parts[3] else ""
        return group + "/" + artifact + "/" + version + "/" + artifact + "-" + version + classifier + "." + ext
    }
}
