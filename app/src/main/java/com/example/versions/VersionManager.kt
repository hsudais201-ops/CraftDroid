package com.example.versions

import com.example.core.db.InstalledVersionDao
import com.example.core.db.InstalledVersionEntity
import com.example.downloader.DownloadManager
import com.example.downloader.DownloadProgress
import com.example.downloader.DownloadTask
import com.example.downloader.HashVerifier
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.minecraft.MinecraftInstaller
import com.example.runtime.JavaRuntimeManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.io.IOException

data class VersionRepairStatus(
    val versionId: String,
    val isJsonValid: Boolean,
    val isJarValid: Boolean,
    val totalLibraries: Int,
    val missingLibraries: Int,
    val totalAssets: Int,
    val missingAssets: Int,
    val isJavaInstalled: Boolean,
    val canLaunch: Boolean
)

class VersionManager(
    private val fileSystem: MinecraftFileSystem,
    private val installer: MinecraftInstaller,
    private val versionParser: VersionJsonParser,
    private val installedVersionDao: InstalledVersionDao,
    private val downloadManager: DownloadManager,
    private val okHttpClient: OkHttpClient,
    private val javaRuntimeManager: JavaRuntimeManager
) {

    private val _versionsList = MutableStateFlow<List<VersionSummary>>(emptyList())
    val versionsList: StateFlow<List<VersionSummary>> = _versionsList.asStateFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private var cachedManifest: VersionManifest? = null

    suspend fun fetchVersions(includeSnapshots: Boolean = false): List<VersionSummary> = withContext(Dispatchers.IO) {
        _isLoading.value = true
        try {
            LauncherLogger.info("Fetching official Minecraft version manifest...")
            val request = Request.Builder()
                .url("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
                .header("Accept", "application/json")
                .build()

            val response = okHttpClient.newCall(request).execute()
            val body = response.body?.string() ?: throw IOException("Empty manifest response")

            val root = JSONObject(body)
            val latest = root.getJSONObject("latest")
            val latestRelease = latest.getString("release")
            val latestSnapshot = latest.getString("snapshot")

            val versionsArr = root.getJSONArray("versions")
            val summaries = mutableListOf<VersionSummary>()

            for (i in 0 until versionsArr.length()) {
                val v = versionsArr.getJSONObject(i)
                val id = v.getString("id")
                val type = v.getString("type")
                val url = v.getString("url")
                val time = v.getString("time")
                val releaseTime = v.getString("releaseTime")
                val sha1 = v.getString("sha1")

                val isInstalled = fileSystem.getVersionJarFile(id).exists() && fileSystem.getVersionJsonFile(id).exists()
                val javaReq = MinecraftJavaRequirements.requiredMajor(id)

                if (includeSnapshots || type == "release") {
                    summaries.add(
                        VersionSummary(
                            id = id,
                            type = type,
                            url = url,
                            time = time,
                            releaseTime = releaseTime,
                            sha1 = sha1,
                            isInstalled = isInstalled,
                            javaRequirement = javaReq
                        )
                    )
                }
            }

            cachedManifest = VersionManifest(
                latestRelease = latestRelease,
                latestSnapshot = latestSnapshot,
                versions = summaries
            )
            _versionsList.value = summaries
            LauncherLogger.info("Loaded ${summaries.size} Minecraft versions from Mojang manifest.")
            summaries
        } catch (e: Exception) {
            LauncherLogger.error("Failed to fetch versions manifest: ${e.message}")
            // Fallback to locally installed versions if offline
            loadLocalVersions()
        } finally {
            _isLoading.value = false
        }
    }

    private suspend fun loadLocalVersions(): List<VersionSummary> {
        val versionsDir = fileSystem.versionsDir
        val localList = mutableListOf<VersionSummary>()
        versionsDir.listFiles()?.filter { it.isDirectory }?.forEach { dir ->
            val id = dir.name
            val jar = File(dir, "$id.jar")
            val json = File(dir, "$id.json")
            if (jar.exists() && json.exists()) {
                localList.add(
                    VersionSummary(
                        id = id,
                        type = "release",
                        url = "",
                        time = "",
                        releaseTime = "Offline",
                        sha1 = "",
                        isInstalled = true,
                        javaRequirement = MinecraftJavaRequirements.requiredMajor(id)
                    )
                )
            }
        }
        _versionsList.value = localList
        return localList
    }

    suspend fun checkRepairStatus(versionId: String): VersionRepairStatus = withContext(Dispatchers.IO) {
        val jsonFile = fileSystem.getVersionJsonFile(versionId)
        val jarFile = fileSystem.getVersionJarFile(versionId)

        var isJsonValid = false
        var isJarValid = false
        var totalLibs = 0
        var missingLibs = 0
        var totalAssets = 0
        var missingAssets = 0

        if (jsonFile.exists()) {
            try {
                val detail = versionParser.parseVersionDetail(jsonFile.readText())
                isJsonValid = true
                isJarValid = jarFile.exists() && jarFile.length() > 0

                totalLibs = detail.libraries.size
                for (lib in detail.libraries) {
                    val art = lib.artifact
                    if (art != null) {
                        val libFile = File(fileSystem.librariesDir, art.path)
                        if (!libFile.exists() || libFile.length() == 0L) {
                            missingLibs++
                        }
                    }
                }

                val indexFile = fileSystem.getAssetIndexFile(detail.assetIndex.id)
                if (indexFile.exists()) {
                    val root = JSONObject(indexFile.readText())
                    val objs = root.optJSONObject("objects")
                    if (objs != null) {
                        totalAssets = objs.length()
                        val keys = objs.keys()
                        while (keys.hasNext()) {
                            val hash = objs.getJSONObject(keys.next()).getString("hash")
                            val assetFile = fileSystem.getAssetObjectFile(hash)
                            if (!assetFile.exists() || assetFile.length() == 0L) {
                                missingAssets++
                            }
                        }
                    }
                } else {
                    missingAssets = 1
                }
            } catch (e: Exception) {
                LauncherLogger.warn("Repair check error: ${e.message}")
            }
        }

        val requiredJava = runCatching { versionParser.parseVersionDetail(jsonFile.readText()).javaVersion.majorVersion }
            .getOrElse { MinecraftJavaRequirements.requiredMajor(versionId) }
        val javaInstalled = javaRuntimeManager.getBestRuntime(requiredJava) != null
        val canLaunch = isJsonValid && isJarValid && missingLibs == 0 && javaInstalled

        VersionRepairStatus(
            versionId = versionId,
            isJsonValid = isJsonValid,
            isJarValid = isJarValid,
            totalLibraries = totalLibs,
            missingLibraries = missingLibs,
            totalAssets = totalAssets,
            missingAssets = missingAssets,
            isJavaInstalled = javaInstalled,
            canLaunch = canLaunch
        )
    }

    suspend fun repairVersion(
        versionId: String,
        onProgress: (DownloadProgress) -> Unit,
        onStatus: (String) -> Unit
    ): Boolean = withContext(Dispatchers.IO) {
        val summary = _versionsList.value.find { it.id == versionId }
        val url = summary?.url
            ?: throw IllegalStateException("No Mojang version-manifest URL is available; refresh the version list before repairing it")
        LauncherLogger.info("Starting automated repair for " + versionId + "...")
        installer.installVersion(versionId, url, onProgress, onStatus)
    }

    suspend fun deleteVersion(versionId: String): Boolean = withContext(Dispatchers.IO) {
        try {
            val vDir = fileSystem.getVersionDir(versionId)
            vDir.deleteRecursively()
            installedVersionDao.deleteInstalledVersion(versionId)
            LauncherLogger.info("Deleted version $versionId from storage.")
            fetchVersions()
            true
        } catch (e: Exception) {
            LauncherLogger.error("Failed to delete $versionId: ${e.message}")
            false
        }
    }
}
