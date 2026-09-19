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

/**
 * Step 23: installs a Fabric launcher profile for an already-installed vanilla
 * Minecraft version. It uses Fabric Meta's standard launcher profile JSON,
 * downloads the declared Fabric libraries, and keeps the vanilla client JAR
 * and natives available under the generated profile id.
 */
data class FabricInstallResult(
    val success: Boolean,
    val profileId: String,
    val loaderVersion: String,
    val downloadedLibraries: Int,
    val error: String? = null
)

class FabricLoaderInstaller(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager,
    private val okHttpClient: OkHttpClient
) {
    suspend fun install(
        minecraftVersion: String,
        loaderVersion: String
    ): FabricInstallResult = withContext(Dispatchers.IO) {
        val url = "https://meta.fabricmc.net/v2/versions/loader/$minecraftVersion/$loaderVersion/profile/json"
        try {
            val vanillaJson = fileSystem.getVersionJsonFile(minecraftVersion)
            val vanillaJar = fileSystem.getVersionJarFile(minecraftVersion)
            if (!vanillaJson.exists() || !vanillaJar.exists()) {
                throw IOException("Minecraft $minecraftVersion must be installed before Fabric")
            }

            LauncherLogger.info("Fetching Fabric profile for Minecraft $minecraftVersion / loader $loaderVersion")
            val request = Request.Builder().url(url).header("Accept", "application/json").build()
            val profileJson = okHttpClient.newCall(request).execute().use { response ->
                if (!response.isSuccessful) throw IOException("Fabric Meta HTTP ${response.code}")
                response.body?.string() ?: throw IOException("Empty Fabric profile response")
            }

            val root = JSONObject(profileJson)
            val profileId = root.optString("id").takeIf { it.isNotBlank() }
                ?: throw IOException("Fabric profile has no id")
            val inheritsFrom = root.optString("inheritsFrom")
            if (inheritsFrom != minecraftVersion) {
                throw IOException("Fabric profile inherits from '$inheritsFrom', expected '$minecraftVersion'")
            }
            val mainClass = root.optString("mainClass")
            if (mainClass.isBlank()) throw IOException("Fabric profile has no mainClass")

            val profileDir = fileSystem.getVersionDir(profileId)
            val profileFile = File(profileDir, "$profileId.json")
            profileFile.writeText(profileJson)

            // LaunchManager checks that a JAR exists for the selected version before
            // resolving inheritsFrom. Copy the vanilla client into the profile.
            val profileJar = File(profileDir, "$profileId.jar")
            if (!profileJar.exists() || profileJar.length() != vanillaJar.length()) {
                vanillaJar.copyTo(profileJar, overwrite = true)
            }

            // Reuse already-extracted vanilla Android natives for the inherited profile.
            val sourceNatives = fileSystem.getNativesDir(minecraftVersion)
            val targetNatives = fileSystem.getNativesDir(profileId)
            if (sourceNatives.exists()) {
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
                val artifact = mavenArtifact(name)
                val baseUrl = lib.optString("url", "https://maven.fabricmc.net/")
                val normalizedBase = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
                val downloadUrl = normalizedBase + artifact.path
                tasks += DownloadTask(
                    url = downloadUrl,
                    destination = File(fileSystem.librariesDir, artifact.path),
                    expectedSha1 = lib.optString("sha1", null).takeIf { !it.isNullOrBlank() },
                    size = lib.optLong("size", 0L),
                    name = name
                )
            }

            // Also download libraries from nested launcherMeta, if a profile ever
            // supplies that representation instead of a flat libraries array.
            val launcherMeta = root.optJSONObject("launcherMeta")
            val metaLibraries = launcherMeta?.optJSONObject("libraries")
            if (metaLibraries != null) {
                for (bucket in listOf("common", "client")) {
                    val arr = metaLibraries.optJSONArray(bucket) ?: continue
                    for (i in 0 until arr.length()) {
                        val lib = arr.optJSONObject(i) ?: continue
                        val name = lib.optString("name")
                        if (name.isBlank()) continue
                        val artifact = mavenArtifact(name)
                        val baseUrl = lib.optString("url", "https://maven.fabricmc.net/")
                        val normalizedBase = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
                        tasks += DownloadTask(
                            url = normalizedBase + artifact.path,
                            destination = File(fileSystem.librariesDir, artifact.path),
                            expectedSha1 = lib.optString("sha1", null).takeIf { !it.isNullOrBlank() },
                            size = lib.optLong("size", 0L),
                            name = name
                        )
                    }
                }
            }

            val uniqueTasks = tasks.distinctBy { it.destination.absolutePath }
            val ok = downloadManager.downloadQueue(uniqueTasks)
            if (!ok) throw IOException("One or more Fabric libraries failed to download")

            LauncherLogger.info("Installed Fabric profile $profileId with ${uniqueTasks.size} libraries")
            FabricInstallResult(true, profileId, loaderVersion, uniqueTasks.size)
        } catch (e: Exception) {
            LauncherLogger.error("Fabric installation failed: ${e.message}")
            FabricInstallResult(false, "fabric-loader-$loaderVersion-$minecraftVersion", loaderVersion, 0, e.message)
        }
    }

    private data class MavenArtifact(val path: String)

    private fun mavenArtifact(name: String): MavenArtifact {
        val parts = name.split(":")
        if (parts.size < 3) throw IOException("Invalid Maven coordinate: $name")
        val group = parts[0].replace('.', '/')
        val artifact = parts[1]
        val versionAndExt = parts[2].split("@", limit = 2)
        val version = versionAndExt[0]
        val extension = if (versionAndExt.size == 2) versionAndExt[1] else "jar"
        val classifier = if (parts.size >= 4) "-${parts[3]}" else ""
        return MavenArtifact("$group/$artifact/$version/$artifact-$version$classifier.$extension")
    }
}
