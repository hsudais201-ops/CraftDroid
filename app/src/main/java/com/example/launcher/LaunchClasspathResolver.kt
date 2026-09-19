package com.example.launcher

import com.example.downloader.HashVerifier
import com.example.logs.LauncherLogger
import com.example.versions.Library
import com.example.versions.VersionDetail
import java.io.File

/** Resolves the exact runtime classpath and rejects missing/corrupt artifacts before JVM startup. */
object LaunchClasspathResolver {
    data class Result(
        val entries: List<File>,
        val missing: List<String>,
        val corrupt: List<String>,
        val duplicates: List<String>
    ) {
        val valid: Boolean get() = missing.isEmpty() && corrupt.isEmpty()
    }

    fun resolve(version: VersionDetail, librariesDir: File, clientJar: File): Result {
        val entries = mutableListOf<File>()
        val missing = mutableListOf<String>()
        val corrupt = mutableListOf<String>()

        version.libraries.forEach { library ->
            library.artifact?.let { artifact ->
                val file = File(librariesDir, artifact.path)
                checkArtifact(file, artifact.sha1, artifact.size, "library ${library.name}", missing, corrupt)
                if (file.isFile && file.length() > 0L) entries += file
            }
        }

        checkArtifact(clientJar, version.clientDownload.sha1, version.clientDownload.size,
            "Minecraft client ${version.id}", missing, corrupt)
        if (clientJar.isFile && clientJar.length() > 0L) entries += clientJar

        val duplicates = entries.groupingBy { it.absolutePath }.eachCount()
            .filterValues { it > 1 }.keys.toList()

        if (missing.isNotEmpty()) missing.forEach { LauncherLogger.error("Classpath missing: $it") }
        if (corrupt.isNotEmpty()) corrupt.forEach { LauncherLogger.error("Classpath corrupt: $it") }
        if (duplicates.isNotEmpty()) LauncherLogger.warn("Duplicate classpath paths detected: ${duplicates.size}")

        return Result(entries.distinctBy { it.absolutePath }, missing, corrupt, duplicates)
    }

    private fun checkArtifact(
        file: File,
        expectedSha1: String?,
        expectedSize: Long,
        label: String,
        missing: MutableList<String>,
        corrupt: MutableList<String>
    ) {
        if (!file.isFile || file.length() == 0L) {
            missing += "$label -> ${file.absolutePath}"
            return
        }
        if (expectedSize > 0L && file.length() != expectedSize) {
            corrupt += "$label -> size ${file.length()} != $expectedSize"
            return
        }
        if (!expectedSha1.isNullOrBlank() && expectedSha1.length == 40 &&
            !HashVerifier.verifySha1(file, expectedSha1)) {
            corrupt += "$label -> SHA-1 mismatch"
        }
    }
}
