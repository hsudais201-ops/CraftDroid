package com.example.minecraft

import com.example.downloader.DownloadManager
import com.example.downloader.DownloadTask
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest

/**
 * Step 38: repairs only the artifacts that can be deterministically reconstructed
 * from the selected Minecraft version metadata.
 */
class InstallationRepairManager(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager
) {
    data class Result(
        val attempted: Int,
        val repaired: Int,
        val failed: List<String>,
        val summary: String
    )

    suspend fun repair(version: VersionDetail): Result = withContext(Dispatchers.IO) {
        val tasks = linkedMapOf<String, DownloadTask>()
        val failedReasons = mutableListOf<String>()

        fun add(key: String, task: DownloadTask) {
            if (!tasks.containsKey(key)) tasks[key] = task
        }

        // Always make the deterministic top-level artifacts repairable.
        add("client", DownloadTask(
            url = version.clientDownload.url,
            destination = fileSystem.getVersionJarFile(version.id),
            expectedSha1 = version.clientDownload.sha1,
            size = version.clientDownload.size,
            name = "${version.id}.jar"
        ))
        add("asset-index", DownloadTask(
            url = version.assetIndex.url,
            destination = fileSystem.getAssetIndexFile(version.assetIndex.id),
            expectedSha1 = version.assetIndex.sha1,
            size = version.assetIndex.size,
            name = "assets/indexes/${version.assetIndex.id}.json"
        ))

        for (library in version.libraries) {
            library.artifact?.let { artifact ->
                add("lib:${artifact.path}", DownloadTask(
                    url = artifact.url,
                    destination = File(fileSystem.librariesDir, artifact.path),
                    expectedSha1 = artifact.sha1.ifBlank { null },
                    size = artifact.size,
                    name = artifact.path
                ))
            }
            library.nativesArtifact?.let { artifact ->
                add("native:${artifact.path}", DownloadTask(
                    url = artifact.url,
                    destination = File(fileSystem.librariesDir, artifact.path),
                    expectedSha1 = artifact.sha1.ifBlank { null },
                    size = artifact.size,
                    name = artifact.path
                ))
            }
        }

        // Assets are content-addressed. Only missing/corrupt objects are queued.
        val indexFile = fileSystem.getAssetIndexFile(version.assetIndex.id)
        if (indexFile.isFile) {
            runCatching {
                val objects = JSONObject(indexFile.readText()).optJSONObject("objects")
                if (objects != null) {
                    val keys = objects.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        val obj = objects.optJSONObject(key) ?: continue
                        val hash = obj.optString("hash")
                        val size = obj.optLong("size", 0L)
                        if (hash.length < 2) continue
                        val destination = fileSystem.getAssetObjectFile(hash)
                        if (!isSha1AndSizeValid(destination, hash, size)) {
                            val prefix = hash.substring(0, 2)
                            add("asset:$hash", DownloadTask(
                                url = "https://resources.download.minecraft.net/$prefix/$hash",
                                destination = destination,
                                expectedSha1 = hash,
                                size = size,
                                name = "asset $key"
                            ))
                        }
                    }
                }
            }.onFailure { failedReasons += "asset index repair scan failed: ${it.message}" }
        }

        if (tasks.isEmpty()) {
            return@withContext Result(0, 0, failedReasons, "Nothing needed repair")
        }

        LauncherLogger.warn("Step 38: repairing ${tasks.size} Minecraft artifacts selectively")
        val before = tasks.keys.toSet()
        val success = downloadManager.downloadQueue(tasks.values.toList(), parallelism = 4)
        val failed = if (success) failedReasons else tasks.values.map { it.name }.toMutableList().apply { addAll(failedReasons) }

        // Re-extract native archives after repair. This is intentionally delegated
        // to the same safe installer extraction path used during installation.
        if (success) {
            try {
                extractNativeLibraries(version)
            } catch (e: Exception) {
                failedReasons += "native extraction failed: ${e.message}"
            }
        }

        val repaired = if (success) before.size else 0
        Result(
            attempted = before.size,
            repaired = repaired,
            failed = failed + failedReasons,
            summary = "attempted=${before.size} repaired=$repaired failed=${(failed + failedReasons).size}"
        )
    }

    private fun extractNativeLibraries(version: VersionDetail) {
        val outputDir = fileSystem.getNativesDir(version.id)
        outputDir.deleteRecursively()
        outputDir.mkdirs()
        for (library in version.libraries) {
            val artifact = library.nativesArtifact ?: continue
            val jar = File(fileSystem.librariesDir, artifact.path)
            if (!jar.isFile) continue
            java.util.zip.ZipFile(jar).use { zip ->
                val entries = zip.entries()
                while (entries.hasMoreElements()) {
                    val entry = entries.nextElement()
                    if (entry.isDirectory) continue
                    val name = entry.name
                    if (!(name.endsWith(".so") || name.endsWith(".dll") || name.endsWith(".dylib"))) continue
                    if (library.extractExcludes.any { name.startsWith(it) } || name.startsWith("META-INF/")) continue
                    val target = File(outputDir, File(name).name)
                    if (!target.canonicalPath.startsWith(outputDir.canonicalPath + File.separator)) continue
                    zip.getInputStream(entry).use { input -> target.outputStream().use { output -> input.copyTo(output) } }
                }
            }
        }
    }

    private fun isSha1AndSizeValid(file: File, sha1: String, size: Long): Boolean {
        if (!file.isFile || (size > 0 && file.length() != size)) return false
        return runCatching {
            val digest = MessageDigest.getInstance("SHA-1")
            file.inputStream().use { input ->
                val buffer = ByteArray(64 * 1024)
                while (true) {
                    val read = input.read(buffer)
                    if (read <= 0) break
                    digest.update(buffer, 0, read)
                }
            }
            digest.digest().joinToString("") { "%02x".format(it) }.equals(sha1, true)
        }.getOrDefault(false)
    }
}
