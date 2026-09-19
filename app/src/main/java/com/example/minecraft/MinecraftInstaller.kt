package com.example.minecraft

import com.example.core.db.InstalledVersionDao
import com.example.core.db.InstalledVersionEntity
import com.example.downloader.DownloadManager
import com.example.downloader.DownloadProgress
import com.example.downloader.DownloadTask
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import com.example.versions.VersionJsonParser
import com.example.versions.VersionInheritanceResolver
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipFile

class MinecraftInstaller(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager,
    private val versionParser: VersionJsonParser,
    private val installedVersionDao: InstalledVersionDao,
    private val okHttpClient: OkHttpClient,
    private val versionInheritanceResolver: VersionInheritanceResolver
) {

    suspend fun installVersion(
        versionId: String,
        versionJsonUrl: String,
        versionJsonSha1: String? = null,
        onProgress: (DownloadProgress) -> Unit,
        onStatus: (String) -> Unit
    ): Boolean = withContext(Dispatchers.IO) {
        try {
            LauncherLogger.info("Starting installation for Minecraft " + versionId + "...")
            installedVersionDao.insertInstalledVersion(
                InstalledVersionEntity(
                    versionId = versionId,
                    type = "release",
                    releaseTime = "",
                    javaRequirement = 0,
                    status = "INSTALLING"
                )
            )
            onStatus("Fetching version metadata...")

            // 1. Download & save Version JSON
            val versionJsonFile = fileSystem.getVersionJsonFile(versionId)
            val jsonSuccess = downloadManager.downloadSingleFile(
                DownloadTask(url = versionJsonUrl, destination = versionJsonFile, expectedSha1 = versionJsonSha1, name = "$versionId.json")
            )
            if (!jsonSuccess || !versionJsonFile.exists()) {
                throw IOException("Failed to download $versionId.json")
            }

            val resolvedVersionJson = versionInheritanceResolver.resolve(versionId, versionJsonFile.readText())
            val versionDetail = versionParser.parseVersionDetail(resolvedVersionJson)

            // 2. Check Storage Space
            val requiredBytes = versionDetail.clientDownload.size + versionDetail.assetIndex.totalSize + 200_000_000L // approx 200MB libraries
            val availableBytes = fileSystem.getAvailableStorageBytes()
            if (availableBytes in 0 until requiredBytes) {
                val reqStr = fileSystem.formatBytes(requiredBytes)
                val availStr = fileSystem.formatBytes(availableBytes)
                throw IOException("Insufficient storage: requires $reqStr, available $availStr")
            }

            // 3. Download Client JAR
            onStatus("Downloading Minecraft client JAR...")
            val clientJarFile = fileSystem.getVersionJarFile(versionId)
            val clientTask = DownloadTask(
                url = versionDetail.clientDownload.url,
                destination = clientJarFile,
                expectedSha1 = versionDetail.clientDownload.sha1,
                size = versionDetail.clientDownload.size,
                name = "$versionId.jar"
            )
            if (!downloadManager.downloadSingleFile(clientTask)) {
                throw IOException("Failed to download client JAR")
            }

            // 4. Collect and download Libraries
            onStatus("Downloading required libraries...")
            val libraryTasks = mutableListOf<DownloadTask>()
            for (lib in versionDetail.libraries) {
                lib.artifact?.let { art ->
                    val destFile = File(fileSystem.librariesDir, art.path)
                    libraryTasks.add(
                        DownloadTask(
                            url = art.url,
                            destination = destFile,
                            expectedSha1 = art.sha1.ifBlank { null },
                            size = art.size,
                            name = destFile.name
                        )
                    )
                }

                lib.nativesArtifact?.let { natArt ->
                    val destFile = File(fileSystem.librariesDir, natArt.path)
                    libraryTasks.add(
                        DownloadTask(
                            url = natArt.url,
                            destination = destFile,
                            expectedSha1 = natArt.sha1.ifBlank { null },
                            size = natArt.size,
                            name = destFile.name
                        )
                    )
                }
            }

            val libSuccess = downloadManager.downloadQueue(libraryTasks, parallelism = 4, onProgressUpdate = onProgress)
            if (!libSuccess) {
                throw IOException("One or more libraries failed to download")
            }

            // 5. Download Asset Index
            onStatus("Downloading asset index...")
            val assetIndexFile = fileSystem.getAssetIndexFile(versionDetail.assetIndex.id)
            val assetIndexTask = DownloadTask(
                url = versionDetail.assetIndex.url,
                destination = assetIndexFile,
                expectedSha1 = versionDetail.assetIndex.sha1,
                size = versionDetail.assetIndex.size,
                name = "indexes/${versionDetail.assetIndex.id}.json"
            )
            if (!downloadManager.downloadSingleFile(assetIndexTask)) {
                throw IOException("Failed to download asset index")
            }

            // 6. Download Asset Objects
            onStatus("Checking and downloading assets...")
            val assetTasks = collectAssetTasks(assetIndexFile)
            val assetsSuccess = downloadManager.downloadQueue(assetTasks, parallelism = 6, onProgressUpdate = onProgress)
            if (!assetsSuccess) {
                throw IOException("One or more Minecraft asset objects failed to download or verify")
            }

            // 7. Extract Native Libraries
            onStatus("Extracting native libraries...")
            extractNativeLibraries(versionDetail, versionId)

            // 8. Register in Installed Versions DB
            installedVersionDao.insertInstalledVersion(
                InstalledVersionEntity(
                    versionId = versionId,
                    type = if (versionId.contains("w") || versionId.contains("pre") || versionId.contains("rc")) "snapshot" else "release",
                    releaseTime = System.currentTimeMillis().toString(),
                    javaRequirement = versionDetail.javaVersion.majorVersion,
                    isCorrupted = false,
                    status = "INSTALLED",
                    clientSha1 = versionDetail.clientDownload.sha1
                )
            )

            LauncherLogger.info("Minecraft $versionId installation completed successfully!")
            onStatus("Installation Complete")
            true
        } catch (e: Exception) {
            val error = e.message ?: e.javaClass.simpleName
            val status = if (error.contains("SHA-1", ignoreCase = true)) "CHECKSUM_FAILED" else "FAILED"
            runCatching {
                installedVersionDao.insertInstalledVersion(
                    InstalledVersionEntity(
                        versionId = versionId,
                        type = "release",
                        releaseTime = "",
                        javaRequirement = 0,
                        isCorrupted = true,
                        status = status,
                        lastError = error
                    )
                )
            }
            LauncherLogger.error("Installation failed for " + versionId + ": " + error)
            onStatus("Error: " + error)
            false
        }
    }

    private fun collectAssetTasks(assetIndexFile: File): List<DownloadTask> {
        val tasks = mutableListOf<DownloadTask>()
        try {
            val root = JSONObject(assetIndexFile.readText())
            val objects = root.optJSONObject("objects") ?: return tasks
            val keys = objects.keys()

            while (keys.hasNext()) {
                val key = keys.next()
                val obj = objects.getJSONObject(key)
                val hash = obj.getString("hash")
                val size = obj.optLong("size", 0L)
                val prefix = hash.substring(0, 2)
                val destFile = fileSystem.getAssetObjectFile(hash)

                val url = "https://resources.download.minecraft.net/$prefix/$hash"
                tasks.add(
                    DownloadTask(
                        url = url,
                        destination = destFile,
                        expectedSha1 = hash,
                        size = size,
                        name = key
                    )
                )
            }
        } catch (e: Exception) {
            LauncherLogger.error("Error reading asset index: ${e.message}")
        }
        return tasks
    }

    private fun extractNativeLibraries(versionDetail: VersionDetail, versionId: String) {
        val nativesDir = fileSystem.getNativesDir(versionId)
        nativesDir.mkdirs()

        for (lib in versionDetail.libraries) {
            val nativeJar = lib.nativesArtifact?.let { File(fileSystem.librariesDir, it.path) }
            if (nativeJar != null && nativeJar.exists()) {
                extractJarSafely(nativeJar, nativesDir, lib.extractExcludes)
            }
        }
    }

    private fun extractJarSafely(jarFile: File, outputDir: File, excludes: List<String>) {
        try {
            ZipFile(jarFile).use { zip ->
                val entries = zip.entries()
                while (entries.hasMoreElements()) {
                    val entry = entries.nextElement()
                    if (entry.isDirectory) continue

                    val name = entry.name
                    // Only extract native shared libraries and metadata
                    if (!name.endsWith(".so") && !name.endsWith(".dll") && !name.endsWith(".dylib")) continue

                    val isExcluded = excludes.any { name.startsWith(it) } || name.startsWith("META-INF/")
                    if (isExcluded) continue

                    val targetFile = File(outputDir, File(name).name)
                    // Protect against Path Traversal
                    if (!targetFile.canonicalPath.startsWith(outputDir.canonicalPath)) {
                        LauncherLogger.warn("Path traversal prevented for zip entry: $name")
                        continue
                    }

                    zip.getInputStream(entry).use { input ->
                        FileOutputStream(targetFile).use { output ->
                            input.copyTo(output)
                        }
                    }
                }
            }
        } catch (e: Exception) {
            LauncherLogger.warn("Error extracting natives from ${jarFile.name}: ${e.message}")
        }
    }
}
