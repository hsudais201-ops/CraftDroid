package com.example.minecraft

import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import java.io.File
import java.security.MessageDigest
import org.json.JSONObject

/**
 * Final on-disk integrity gate before a Minecraft JVM is started.
 * It verifies the files described by the selected Mojang version manifest,
 * rather than trusting that a file merely exists.
 */
class GameInstallationVerifier(private val fileSystem: MinecraftFileSystem) {

    data class Result(
        val valid: Boolean,
        val errors: List<String>,
        val warnings: List<String>,
        val checkedFiles: Int,
        val checkedAssets: Int
    ) {
        val summary: String
            get() = "files=$checkedFiles assets=$checkedAssets errors=${errors.size} warnings=${warnings.size}"
    }

    fun verify(version: VersionDetail, verifyAssetHashes: Boolean = true): Result {
        val errors = mutableListOf<String>()
        val warnings = mutableListOf<String>()
        var files = 0
        var assets = 0

        fun checkFile(file: File, sha1: String?, expectedSize: Long?, label: String) {
            if (!file.isFile) {
                errors += "$label is missing: ${file.absolutePath}"
                return
            }
            files++
            if (expectedSize != null && expectedSize > 0 && file.length() != expectedSize) {
                errors += "$label has wrong size (${file.length()} != $expectedSize)"
                return
            }
            if (!sha1.isNullOrBlank()) {
                val actual = sha1(file)
                if (!actual.equals(sha1, ignoreCase = true)) {
                    errors += "$label has SHA-1 mismatch"
                }
            }
        }

        checkFile(
            fileSystem.getVersionJarFile(version.id),
            version.clientDownload.sha1,
            version.clientDownload.size,
            "Minecraft client JAR"
        )

        val indexFile = fileSystem.getAssetIndexFile(version.assetIndex.id)
        checkFile(indexFile, version.assetIndex.sha1, version.assetIndex.size, "Asset index")

        for (library in version.libraries) {
            library.artifact?.let { artifact ->
                checkFile(
                    File(fileSystem.librariesDir, artifact.path),
                    artifact.sha1,
                    artifact.size,
                    "Library ${library.name}"
                )
            }
            library.nativesArtifact?.let { artifact ->
                checkFile(
                    File(fileSystem.librariesDir, artifact.path),
                    artifact.sha1,
                    artifact.size,
                    "Native archive ${library.name}"
                )
            }
        }

        val nativesDir = fileSystem.getNativesDir(version.id)
        val hasNativeDependencies = version.libraries.any { it.nativesArtifact != null }
        if (hasNativeDependencies) {
            val nativeFiles = nativesDir.listFiles()?.filter { it.isFile && it.extension.equals("so", true) } ?: emptyList()
            if (nativeFiles.isEmpty()) {
                warnings += "Version declares native libraries but extracted natives directory contains no .so files"
            }
        }

        if (indexFile.isFile) {
            try {
                val objects = JSONObject(indexFile.readText()).optJSONObject("objects")
                if (objects == null) {
                    errors += "Asset index has no objects map"
                } else {
                    val keys = objects.keys()
                    while (keys.hasNext()) {
                        val key = keys.next()
                        val obj = objects.optJSONObject(key) ?: continue
                        val hash = obj.optString("hash")
                        val size = obj.optLong("size", -1L)
                        if (hash.length < 2) {
                            errors += "Asset $key has an invalid hash"
                            continue
                        }
                        val assetFile = fileSystem.getAssetObjectFile(hash)
                        if (!assetFile.isFile) {
                            errors += "Missing asset object: $key"
                        } else if (size >= 0 && assetFile.length() != size) {
                            errors += "Asset $key has wrong size"
                        } else if (verifyAssetHashes) {
                            val actual = sha1(assetFile)
                            if (!actual.equals(hash, ignoreCase = true)) {
                                errors += "Asset $key has SHA-1 mismatch"
                            }
                        }
                        assets++
                    }
                }
            } catch (e: Exception) {
                errors += "Unable to parse asset index: ${e.message}"
            }
        }

        val result = Result(errors.isEmpty(), errors, warnings, files, assets)
        if (result.valid) {
            LauncherLogger.info("Minecraft installation integrity check passed: ${result.summary}")
        } else {
            LauncherLogger.error("Minecraft installation integrity check failed: ${result.summary}")
            result.errors.take(12).forEach { LauncherLogger.error("Install check: $it") }
            if (result.errors.size > 12) LauncherLogger.error("Install check: ${result.errors.size - 12} more errors")
        }
        result.warnings.forEach { LauncherLogger.warn("Install check: $it") }
        return result
    }

    private fun sha1(file: File): String {
        val digest = MessageDigest.getInstance("SHA-1")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
