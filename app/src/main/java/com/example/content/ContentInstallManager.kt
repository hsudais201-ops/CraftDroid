package com.example.content

import com.example.downloader.DownloadManager
import com.example.downloader.DownloadTask
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.zip.ZipFile

data class ContentInstallResult(val installedFiles: List<File>, val dependencies: List<String> = emptyList())

class ContentInstallManager(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager,
    private val modrinth: ModrinthClient,
    private val curseForge: CurseForgeClient
) {
    suspend fun installModrinthVersion(projectId: String, minecraftVersion: String, loader: String?, destinationDir: File): ContentInstallResult =
        withContext(Dispatchers.IO) {
            destinationDir.mkdirs()
            val root = modrinth.resolveBestVersion(projectId, minecraftVersion, loader)
            val deps = modrinth.resolveRequiredDependencies(root, minecraftVersion, loader)
            val versions = listOf(root) + deps
            val tasks = versions.mapNotNull { version ->
                val file = version.files.firstOrNull { it.primary } ?: version.files.firstOrNull()
                file?.takeIf { it.url.isNotBlank() }?.let {
                    DownloadTask(it.url, safeChild(destinationDir, it.fileName), it.sha1, it.size, version.name.ifBlank { it.fileName })
                }
            }
            if (tasks.size != versions.size) throw IOException("One or more Modrinth versions has no downloadable primary file")
            if (!downloadManager.downloadQueue(tasks, parallelism = 3)) throw IOException("Modrinth content download failed")
            ContentInstallResult(tasks.map { it.destination }, deps.map { it.projectId ?: it.id })
        }

    suspend fun installModrinthMrpack(mrpackFile: File, instanceRoot: File): ContentInstallResult = withContext(Dispatchers.IO) {
        if (!mrpackFile.isFile) throw IOException("Modrinth .mrpack file is missing")
        instanceRoot.mkdirs()
        val tasks = mutableListOf<DownloadTask>()
        ZipFile(mrpackFile).use { zip ->
            val entry = zip.getEntry("modrinth.index.json") ?: throw IOException("Invalid .mrpack: index is missing")
            val index = zip.getInputStream(entry).bufferedReader().use { JSONObject(it.readText()) }
            if (!index.optString("format_type").equals("modrinth", true)) throw IOException("Unsupported Modrinth pack format")
            val files = index.optJSONArray("files") ?: JSONArray()
            for (i in 0 until files.length()) {
                val item = files.optJSONObject(i) ?: continue
                val path = item.optString("path")
                val downloads = item.optJSONArray("downloads") ?: JSONArray()
                val url = downloads.optString(0)
                if (path.isBlank() || url.isBlank()) throw IOException("Invalid .mrpack file entry at index " + i)
                tasks += DownloadTask(
                    url = url,
                    destination = safeChild(instanceRoot, path),
                    expectedSha1 = item.optJSONObject("hashes")?.optString("sha1")?.takeIf { it.isNotBlank() },
                    size = item.optLong("file_size", 0L),
                    name = path
                )
            }
            val copied = copyZipPrefix(zip, "overrides/", instanceRoot)
            if (tasks.isNotEmpty() && !downloadManager.downloadQueue(tasks, parallelism = 4)) {
                throw IOException("Modrinth .mrpack files failed to download")
            }
            ContentInstallResult(tasks.map { it.destination } + copied)
        }
    }

    suspend fun installCurseForgeFile(
        modId: Long,
        fileId: Long,
        destinationDir: File,
        minecraftVersion: String,
        loaderType: Int?
    ): ContentInstallResult = withContext(Dispatchers.IO) {
        destinationDir.mkdirs()
        val project = curseForge.getProject(modId)
        val rootFile = curseForge.getFile(modId, fileId)
        val dependencies = curseForge.resolveRequiredDependencies(rootFile, minecraftVersion, loaderType)
        val allFiles = listOf(rootFile) + dependencies
        val tasks = allFiles.map { item ->
            DownloadTask(
                url = curseForge.distributionUrl(item.modId, item.id),
                destination = safeChild(destinationDir, item.fileName),
                size = item.fileLength,
                name = item.fileName
            )
        }
        if (!downloadManager.downloadQueue(tasks, parallelism = 3)) throw IOException("CurseForge content download failed")
        LauncherLogger.info("Installed CurseForge " + project.name + " with " + dependencies.size + " required dependencies")
        ContentInstallResult(tasks.map { it.destination }, dependencies.map { it.fileName })
    }

    suspend fun installCurseForgeWorld(modId: Long, fileId: Long): ContentInstallResult = withContext(Dispatchers.IO) {
        val file = curseForge.getFile(modId, fileId)
        val archive = File(fileSystem.runtimeDir, "downloads/curseforge-world-" + file.id + ".zip")
        archive.parentFile?.mkdirs()
        val ok = downloadManager.downloadSingleFile(DownloadTask(curseForge.distributionUrl(modId, fileId), archive, size = file.fileLength, name = file.fileName))
        if (!ok) throw IOException("CurseForge world download failed")
        val installed = extractZipSafely(archive, fileSystem.savesDir)
        archive.delete()
        ContentInstallResult(installed)
    }

    suspend fun installCurseForgeModpack(manifestZip: File, instanceRoot: File): ContentInstallResult = withContext(Dispatchers.IO) {
        instanceRoot.mkdirs()
        val tasks = mutableListOf<DownloadTask>()
        ZipFile(manifestZip).use { zip ->
            val entry = zip.getEntry("manifest.json") ?: throw IOException("Invalid CurseForge modpack: manifest.json is missing")
            val manifest = zip.getInputStream(entry).bufferedReader().use { JSONObject(it.readText()) }
            if (!manifest.optString("manifestType").equals("minecraftModpack", true)) throw IOException("Unsupported CurseForge pack manifest")
            val files = manifest.optJSONArray("files") ?: JSONArray()
            for (i in 0 until files.length()) {
                val item = files.optJSONObject(i) ?: continue
                if (!item.optBoolean("required", true)) continue
                val projectId = item.optLong("projectID", 0L)
                val fileId = item.optLong("fileID", 0L)
                if (projectId <= 0L || fileId <= 0L) throw IOException("Invalid CurseForge manifest file entry at " + i)
                val meta = curseForge.getFile(projectId, fileId)
                tasks += DownloadTask(
                    url = curseForge.distributionUrl(projectId, fileId),
                    destination = safeChild(instanceRoot, "mods/" + meta.fileName),
                    size = meta.fileLength,
                    name = meta.fileName
                )
            }
            val overrides = copyZipPrefix(zip, "overrides/", instanceRoot)
            if (tasks.isNotEmpty() && !downloadManager.downloadQueue(tasks, parallelism = 4)) {
                throw IOException("CurseForge modpack files failed to download")
            }
            ContentInstallResult(tasks.map { it.destination } + overrides)
        }
    }

    private fun safeChild(root: File, relative: String): File {
        val normalized = relative.replace('\\', '/').trimStart('/')
        require(normalized.isNotBlank() && !normalized.split('/').any { it == ".." }) { "Unsafe content path: " + relative }
        val child = File(root, normalized).canonicalFile
        val base = root.canonicalFile
        require(child.path == base.path || child.path.startsWith(base.path + File.separator)) { "Unsafe content path: " + relative }
        child.parentFile?.mkdirs()
        return child
    }

    private fun copyZipPrefix(zip: ZipFile, prefix: String, destination: File): List<File> {
        val files = mutableListOf<File>()
        zip.entries().asSequence().forEach { entry ->
            if (entry.isDirectory || !entry.name.startsWith(prefix)) return@forEach
            val relative = entry.name.removePrefix(prefix)
            if (relative.isBlank()) return@forEach
            val out = safeChild(destination, relative)
            zip.getInputStream(entry).use { input -> FileOutputStream(out).use { input.copyTo(it) } }
            files += out
        }
        return files
    }

    private fun extractZipSafely(archive: File, destination: File): List<File> {
        val files = mutableListOf<File>()
        ZipFile(archive).use { zip ->
            zip.entries().asSequence().forEach { entry ->
                if (entry.isDirectory) return@forEach
                val out = safeChild(destination, entry.name)
                zip.getInputStream(entry).use { input -> FileOutputStream(out).use { input.copyTo(it) } }
                files += out
            }
        }
        if (files.none { it.name == "level.dat" }) {
            LauncherLogger.warn("CurseForge world archive installed without an immediately visible level.dat; inspect the resulting saves folder.")
        }
        return files
    }
}
