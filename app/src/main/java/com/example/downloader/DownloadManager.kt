package com.example.downloader

import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong

data class DownloadTask(
    val url: String,
    val destination: File,
    val expectedSha1: String? = null,
    val size: Long = 0L,
    val name: String = destination.name
)

data class DownloadProgress(
    val totalFiles: Int = 0,
    val completedFiles: Int = 0,
    val totalBytes: Long = 0L,
    val downloadedBytes: Long = 0L,
    val currentFileName: String = "",
    val speedBytesPerSec: Long = 0L,
    val etaSeconds: Long = 0L,
    val isIndeterminate: Boolean = false,
    val isRunning: Boolean = false,
    val error: String? = null
) {
    val progressFraction: Float
        get() = if (totalBytes > 0) (downloadedBytes.toFloat() / totalBytes.toFloat()).coerceIn(0f, 1f)
        else if (totalFiles > 0) (completedFiles.toFloat() / totalFiles.toFloat()).coerceIn(0f, 1f)
        else 0f

    val formattedSpeed: String
        get() = String.format("%.2f MB/s", speedBytesPerSec.toDouble() / (1024 * 1024))
}

class DownloadManager(private val okHttpClient: OkHttpClient) {

    private val _progress = MutableStateFlow(DownloadProgress())
    val progress: StateFlow<DownloadProgress> = _progress.asStateFlow()

    @Volatile
    private var isCancelled = false

    fun cancel() {
        isCancelled = true
    }

    suspend fun downloadSingleFile(
        task: DownloadTask,
        verifyHash: Boolean = true,
        maxRetries: Int = 3
    ): Boolean = withContext(Dispatchers.IO) {
        isCancelled = false
        val existingValid = task.destination.exists() && task.destination.length() > 0 &&
            (!verifyHash || HashVerifier.verifySha1(task.destination, task.expectedSha1))
        if (existingValid) return@withContext true

        var attempt = 0
        while (attempt < maxRetries && !isCancelled) {
            attempt++
            try {
                val ok = downloadResumable(task) { downloaded ->
                    _progress.value = DownloadProgress(
                        totalFiles = 1,
                        completedFiles = 0,
                        totalBytes = task.size,
                        downloadedBytes = downloaded,
                        currentFileName = task.name,
                        isRunning = true,
                        isIndeterminate = task.size <= 0
                    )
                }
                if (ok) {
                    _progress.value = DownloadProgress(
                        totalFiles = 1,
                        completedFiles = 1,
                        totalBytes = task.size,
                        downloadedBytes = if (task.size > 0) task.size else task.destination.length(),
                        currentFileName = task.name,
                        isRunning = false
                    )
                    return@withContext true
                }
            } catch (e: Exception) {
                LauncherLogger.warn("Attempt $attempt failed for ${task.name}: ${e.message}")
                if (attempt >= maxRetries) {
                    _progress.value = _progress.value.copy(isRunning = false, error = e.message ?: "Download failed")
                    LauncherLogger.error("Failed to download ${task.name} after $maxRetries attempts.")
                    return@withContext false
                }
            }
        }
        _progress.value = _progress.value.copy(isRunning = false, error = if (isCancelled) "Download cancelled" else "Download failed")
        false
    }

    suspend fun downloadQueue(
        tasks: List<DownloadTask>,
        parallelism: Int = 1,
        onProgressUpdate: ((DownloadProgress) -> Unit)? = null
    ): Boolean = withContext(Dispatchers.IO) {
        isCancelled = false
        if (tasks.isEmpty()) {
            _progress.value = DownloadProgress()
            return@withContext true
        }

        val totalFiles = tasks.size
        val totalBytes = tasks.sumOf { it.size.coerceAtLeast(0L) }
        var completedFiles = 0
        var completedBytes = 0L

        _progress.value = DownloadProgress(
            totalFiles = totalFiles,
            completedFiles = 0,
            totalBytes = totalBytes,
            downloadedBytes = 0L,
            isRunning = true
        )

        for (task in tasks) {
            if (isCancelled) break

            val ok = try {
                downloadResumable(task) { currentFileBytes ->
                    val progress = DownloadProgress(
                        totalFiles = totalFiles,
                        completedFiles = completedFiles,
                        totalBytes = totalBytes,
                        downloadedBytes = (completedBytes + currentFileBytes).coerceAtMost(totalBytes.takeIf { it > 0 } ?: Long.MAX_VALUE),
                        currentFileName = task.name,
                        isRunning = true,
                        isIndeterminate = totalBytes <= 0L
                    )
                    _progress.value = progress
                    onProgressUpdate?.invoke(progress)
                }
            } catch (e: Exception) {
                LauncherLogger.error("Failed to download ${task.name}: ${e.message}")
                false
            }

            if (!ok) {
                _progress.value = _progress.value.copy(
                    isRunning = false,
                    error = if (isCancelled) "Download cancelled" else "Failed to download ${task.name}"
                )
                return@withContext false
            }

            completedFiles++
            completedBytes += if (task.size > 0) task.size else task.destination.length()
            val progress = DownloadProgress(
                totalFiles = totalFiles,
                completedFiles = completedFiles,
                totalBytes = totalBytes,
                downloadedBytes = completedBytes.coerceAtMost(totalBytes.takeIf { it > 0 } ?: Long.MAX_VALUE),
                currentFileName = task.name,
                isRunning = completedFiles < totalFiles
            )
            _progress.value = progress
            onProgressUpdate?.invoke(progress)
        }

        val success = completedFiles == totalFiles && !isCancelled
        _progress.value = _progress.value.copy(
            completedFiles = completedFiles,
            downloadedBytes = completedBytes.coerceAtMost(totalBytes.takeIf { it > 0 } ?: Long.MAX_VALUE),
            isRunning = false,
            error = if (success) null else if (isCancelled) "Download cancelled" else "Some files failed to download"
        )
        success
    }

    private fun downloadResumable(
        task: DownloadTask,
        onBytes: (Long) -> Unit
    ): Boolean {
        val parent = task.destination.parentFile ?: throw IOException("Download destination has no parent directory")
        val tempFile = File(parent, task.destination.name + ".part")
        parent.mkdirs()

        if (tempFile.exists() && task.size > 0 && tempFile.length() == task.size &&
            (!task.expectedSha1.isNullOrBlank() && HashVerifier.verifySha1(tempFile, task.expectedSha1))
        ) {
            if (tempFile.renameTo(task.destination) || tempFile.copyTo(task.destination, overwrite = true).exists()) {
                tempFile.delete()
                onBytes(task.destination.length())
                return true
            }
        }

        var attempt = 0
        while (attempt < 3 && !isCancelled) {
            attempt++
            var resumeAt = if (tempFile.isFile) tempFile.length() else 0L
            try {
                val builder = Request.Builder()
                    .url(task.url)
                    .header("User-Agent", "CraftDroid-Launcher/1.3")
                if (resumeAt > 0L) builder.header("Range", "bytes=$resumeAt-")

                okHttpClient.newCall(builder.build()).execute().use { response ->
                    if (!response.isSuccessful && response.code != 206) {
                        throw IOException("HTTP ${response.code}")
                    }
                    val append = resumeAt > 0L && response.code == 206
                    if (!append) {
                        tempFile.delete()
                        resumeAt = 0L
                    }

                    val body = response.body ?: throw IOException("Empty body")
                    var downloaded = resumeAt
                    body.byteStream().use { input ->
                        FileOutputStream(tempFile, append).use { output ->
                            val buffer = ByteArray(64 * 1024)
                            while (true) {
                                if (isCancelled) throw IOException("Cancelled")
                                val read = input.read(buffer)
                                if (read < 0) break
                                output.write(buffer, 0, read)
                                downloaded += read
                                onBytes(downloaded)
                            }
                            output.fd.sync()
                        }
                    }
                }

                val actualSize = tempFile.length()
                if (task.size > 0 && actualSize != task.size) {
                    throw IOException("Size mismatch for ${task.name}: expected ${task.size}, got $actualSize")
                }
                if (!task.expectedSha1.isNullOrBlank() && !HashVerifier.verifySha1(tempFile, task.expectedSha1)) {
                    throw IOException("SHA-1 mismatch for ${task.name}")
                }

                if (tempFile.renameTo(task.destination) || tempFile.copyTo(task.destination, overwrite = true).exists()) {
                    tempFile.delete()
                    onBytes(task.destination.length())
                    return true
                }
                throw IOException("Unable to commit ${task.name}")
            } catch (e: Exception) {
                if (isCancelled) return false
                LauncherLogger.warn("Resumable download attempt $attempt failed for ${task.name}: ${e.message}")
            }
        }
        return false
    }
}
