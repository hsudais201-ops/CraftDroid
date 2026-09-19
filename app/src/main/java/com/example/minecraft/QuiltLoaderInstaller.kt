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
    suspend fun install(minecraftVersion: String, loaderVersion: String): QuiltInstallResult = withContext(Dispatchers.IO) {
        val url = "https://meta.quiltmc.org/v3/versions/loader/" + minecraftVersion + "/" + loaderVersion + "/profile/json"
        try {
            val vanillaJar = fileSystem.getVersionJarFile(minecraftVersion)
            if (!fileSystem.getVersionJsonFile(minecraftVersion).exists() || !vanillaJar.exists()) {
                throw IOException("Minecraft " + minecraftVersion + " must be installed before Quilt")
            }

            val request = Request.Builder()
                .url(url)
                .header("Accept", "application/json")
                .header("User-Agent", "CraftDroid-Launcher/2.5")
                .build()

            val profileJson = okHttpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("Quilt Meta HTTP " + response.code)
                response.body?.string() ?: throw IOException("Empty Quilt profile response")
            }

            val root = JSONObject(profileJson)
            val profileId = root.optString("id").takeIf { it.isNotBlank() }
                ?: throw IOException("Quilt profile has no id")
            val inheritsFrom = root.optString("inheritsFrom")
            if (inheritsFrom != minecraftVersion) {
                throw IOException("Quilt profile inherits from '" + inheritsFrom + "', expected '" + minecraftVersion + "'")
            }
            if (root.optString("mainClass").isBlank()) throw IOException("Quilt profile has no mainClass")

            val profileDir = fileSystem.getVersionDir(profileId)
            File(profileDir, profileId + ".json").writeText(profileJson)

            val profileJar = File(profileDir, profileId + ".jar")
            if (!profileJar.exists() || profileJar.length() != vanillaJar.length()) {
                vanillaJar.copyTo(profileJar, overwrite = true)
            }

            val sourceNatives = fileSystem.getNativesDir(minecraftVersion)
            val targetNatives = fileSystem.getNativesDir(profileId)
            if (sourceNatives.exists()) {
                sourceNatives.listFiles()?.forEach { source ->
                    if (source.isFile && source.extension.equals("so", true)) {
                        source.copyTo(File(targetNatives, source.name), overwrite = true)
                    }
                }
            }

            val tasks = mutableListOf<DownloadTask>()
            val libraries = root.optJSONArray("libraries") ?: JSONArray()
            for (i in 0 until libraries.length()) {
                addLibraryTask(libraries.optJSONObject(i), "https://maven.quiltmc.org/repository/release/")?.let(tasks::add)
            }

            val metaLibraries = root.optJSONObject("launcherMeta")?.optJSONObject("libraries")
            if (metaLibraries != null) {
                for (bucket in listOf("common", "client")) {
                    val arr = metaLibraries.optJSONArray(bucket) ?: continue
                    for (i in 0 until arr.length()) {
                        addLibraryTask(arr.optJSONObject(i), "https://maven.quiltmc.org/repository/release/")?.let(tasks::add)
                    }
                }
            }

            val uniqueTasks = tasks.distinctBy { it.destination.absolutePath }
            if (!downloadManager.downloadQueue(uniqueTasks)) {
                throw IOException("One or more Quilt libraries failed to download")
            }

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

    private fun addLibraryTask(lib: JSONObject?, defaultBase: String): DownloadTask? {
        if (lib == null) return null
        val name = lib.optString("name").trim()
        if (name.isBlank()) return null

        val parts = name.split(":")
        if (parts.size < 3) throw IOException("Invalid Maven coordinate: " + name)
        val group = parts[0].replace(".", "/")
        val artifact = parts[1]
        val versionAndExt = parts[2].split("@", limit = 2)
        val version = versionAndExt[0]
        val extension = if (versionAndExt.size == 2) versionAndExt[1] else "jar"
        val classifier = if (parts.size >= 4) "-" + parts[3] else ""
        val path = group + "/" + artifact + "/" + version + "/" + artifact + "-" + version + classifier + "." + extension

        val rawUrl = lib.optString("url", defaultBase)
        val base = if (rawUrl.endsWith("/")) rawUrl else rawUrl + "/"
        return DownloadTask(
            url = base + path,
            destination = File(fileSystem.librariesDir, path),
            expectedSha1 = lib.optString("sha1").takeIf { it.isNotBlank() },
            size = lib.optLong("size", 0L),
            name = name
        )
    }
}
