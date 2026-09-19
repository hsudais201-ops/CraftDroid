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
        if (task.destination.exists() && task.destination.length() > 0) {
            if (!verifyHash || HashVerifier.verifySha1(task.destination, task.expectedSha1)) {
                return@withContext true
            }
        }

        var attempt = 0
        while (attempt < maxRetries && !isCancelled) {
            attempt++
            try {
                task.destination.parentFile?.mkdirs()
                val tempFile = File(task.destination.parentFile, "${task.destination.name}.download")

                val resumeBytes = if (tempFile.isFile) tempFile.length() else 0L
                val requestBuilder = Request.Builder()
                    .url(task.url)
                    .header("User-Agent", "CraftDroid-Launcher/1.4")
                if (resumeBytes > 0L) requestBuilder.header("Range", "bytes=$resumeBytes-")
                val request = requestBuilder.build()

                okHttpClient.newCall(request).execute().use { response ->
                    if (response.code == 416 && resumeBytes > 0L) {
                        tempFile.delete()
                        throw IOException("HTTP 416; partial download reset for ${task.name}")
                    }
                    if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                    val body = response.body ?: throw IOException("Empty body")

                    body.byteStream().use { input ->
                        FileOutputStream(tempFile, resumeBytes > 0L && response.code == 206).use { output ->
                            input.copyTo(output)
                        }
                    }
                }

                if (task.size > 0L && tempFile.length() != task.size) {
                    throw IOException("Size mismatch for " + task.name + ": " + tempFile.length() + "/" + task.size)
                }

                if (verifyHash && !task.expectedSha1.isNullOrBlank()) {
                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {
                        tempFile.delete()
                        throw IOException("SHA-1 mismatch for ${task.name}")
                    }
                }

                if (tempFile.renameTo(task.destination) || tempFile.copyTo(task.destination, overwrite = true).exists()) {
                    tempFile.delete()
                    return@withContext true
                }
            } catch (e: Exception) {
                LauncherLogger.warn("Attempt $attempt failed for ${task.name}: ${e.message}")
                if (attempt >= maxRetries) {
                    LauncherLogger.error("Failed to download ${task.name} after $maxRetries attempts.")
                    return@withContext false
                }
            }
        }
        false
    }

    suspend fun downloadQueue(
        tasks: List<DownloadTask>,
        parallelism: Int = 4,
        onProgressUpdate: ((DownloadProgress) -> Unit)? = null
    ): Boolean = withContext(Dispatchers.IO) {
        isCancelled = false
        val totalFiles = tasks.size
        val totalBytes = tasks.sumOf { it.size }
        val completedCount = AtomicInteger(0)
        val downloadedBytesCounter = AtomicLong(0L)

        val startTime = System.currentTimeMillis()
        var lastSampleTime = startTime
        var lastBytes = 0L
        var currentSpeed = 0L

        val semaphore = Semaphore(parallelism)
        var hasFailures = false

        _progress.value = DownloadProgress(
            totalFiles = totalFiles,
            completedFiles = 0,
            totalBytes = totalBytes,
            downloadedBytes = 0L,
            isRunning = true
        )

        kotlinx.coroutines.coroutineScope {
            val jobs = tasks.map { task ->
                async {
                    if (isCancelled) return@async false
                    semaphore.withPermit {
                        if (isCancelled) return@withPermit false

                        // Check if already downloaded and valid
                        if (task.destination.exists() && task.destination.length() > 0) {
                            if (task.expectedSha1.isNullOrBlank() || HashVerifier.verifySha1(task.destination, task.expectedSha1)) {
                                completedCount.incrementAndGet()
                                downloadedBytesCounter.addAndGet(task.destination.length())
                                return@withPermit true
                            }
                        }

                        var success = false
                        var attempts = 0
                        while (attempts < 3 && !success && !isCancelled) {
                            attempts++
                            try {
                                task.destination.parentFile?.mkdirs()
                                val tempFile = File(task.destination.parentFile, "${task.destination.name}.tmp")

                                val resumeBytes = if (tempFile.isFile) tempFile.length() else 0L
                                val requestBuilder = Request.Builder()
                                    .url(task.url)
                                    .header("User-Agent", "CraftDroid-Launcher/1.4")
                                if (resumeBytes > 0L) requestBuilder.header("Range", "bytes=$resumeBytes-")
                                val request = requestBuilder.build()

                                okHttpClient.newCall(request).execute().use { response ->
                                    if (response.code == 416 && resumeBytes > 0L) {
                                        tempFile.delete()
                                        throw IOException("HTTP 416; partial download reset for ${task.name}")
                                    }
                                    if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
                                    val body = response.body ?: throw IOException("Empty body")

                                    val buffer = ByteArray(8192)
                                    body.byteStream().use { input ->
                                        FileOutputStream(tempFile, resumeBytes > 0L && response.code == 206).use { output ->
                                            var bytesRead: Int
                                            while (input.read(buffer).also { bytesRead = it } != -1) {
                                                if (isCancelled) throw IOException("Cancelled")
                                                output.write(buffer, 0, bytesRead)
                                                val currentTotal = downloadedBytesCounter.addAndGet(bytesRead.toLong())

                                                // Update speed calculation every 500ms
                                                val now = System.currentTimeMillis()
                                                if (now - lastSampleTime > 500) {
                                                    val deltaBytes = currentTotal - lastBytes
                                                    val deltaTimeSec = (now - lastSampleTime).toDouble() / 1000.0
                                                    if (deltaTimeSec > 0) {
                                                        currentSpeed = (deltaBytes / deltaTimeSec).toLong()
                                                    }
                                                    lastBytes = currentTotal
                                                    lastSampleTime = now

                                                    val remainingBytes = (totalBytes - currentTotal).coerceAtLeast(0L)
                                                    val eta = if (currentSpeed > 0) remainingBytes / currentSpeed else 0L

                                                    val p = DownloadProgress(
                                                        totalFiles = totalFiles,
                                                        completedFiles = completedCount.get(),
                                                        totalBytes = totalBytes,
                                                        downloadedBytes = currentTotal,
                                                        currentFileName = task.name,
                                                        speedBytesPerSec = currentSpeed,
                                                        etaSeconds = eta,
                                                        isRunning = true
                                                    )
                                                    _progress.value = p
                                                    onProgressUpdate?.invoke(p)
                                                }
                                            }
                                        }
                                    }
                                }

                                if (task.size > 0L && tempFile.length() != task.size) {
                                    throw IOException("Size mismatch for " + task.name + ": " + tempFile.length() + "/" + task.size)
                                }

                                if (!task.expectedSha1.isNullOrBlank()) {
                                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {
                                        tempFile.delete()
                                        throw IOException("SHA-1 hash check failed")
                                    }
                                }

                                if (tempFile.renameTo(task.destination) || tempFile.copyTo(task.destination, overwrite = true).exists()) {
                                    tempFile.delete()
                                    success = true
                                    completedCount.incrementAndGet()
                                }
                            } catch (e: Exception) {
                                if (isCancelled) return@withPermit false
                                if (attempts >= 3) {
                                    LauncherLogger.error("Failed to download ${task.name}: ${e.message}")
                                }
                            }
                        }
                        success
                    }
                }
            }

            for (job in jobs) {
                val result = job.await()
                if (!result) hasFailures = true
            }
        }

        _progress.value = _progress.value.copy(
            completedFiles = completedCount.get(),
            isRunning = false,
            error = if (hasFailures) "Some files failed to download" else null
        )
        !hasFailures && !isCancelled
    }
}
