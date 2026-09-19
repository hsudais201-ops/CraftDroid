package com.example.filesystem

import android.content.Context
import android.os.Environment
import android.os.StatFs
import java.io.File

/**
 * Manages the canonical Minecraft Java Edition directory hierarchy on Android.
 * Compatible with standard Minecraft layouts and Android scoped storage constraints.
 */
class MinecraftFileSystem(private val context: Context) {

    val rootDir: File by lazy {
        // Prefer external files dir (Android/data/com.../files/Minecraft) for ample storage,
        // fallback to internal files dir if external is unavailable.
        val external = context.getExternalFilesDir(null)
        val base = external ?: context.filesDir
        File(base, "Minecraft").apply { mkdirs() }
    }

    val versionsDir: File get() = File(rootDir, "versions").apply { mkdirs() }
    val librariesDir: File get() = File(rootDir, "libraries").apply { mkdirs() }
    val assetsDir: File get() = File(rootDir, "assets").apply { mkdirs() }
    val assetIndexesDir: File get() = File(assetsDir, "indexes").apply { mkdirs() }
    val assetObjectsDir: File get() = File(assetsDir, "objects").apply { mkdirs() }
    /**
     * Executable JVMs must live in app-private internal storage on Android.
     * Some external/scoped-storage locations can be mounted noexec.
     */
    val runtimeDir: File get() = File(context.filesDir, "minecraft-runtime").apply { mkdirs() }
    val javaDir: File get() = File(runtimeDir, "java").apply { mkdirs() }
    val rendererDir: File get() = File(runtimeDir, "renderer").apply { mkdirs() }
    val modsDir: File get() = File(rootDir, "mods").apply { mkdirs() }
    val resourcePacksDir: File get() = File(rootDir, "resourcepacks").apply { mkdirs() }
    val shaderPacksDir: File get() = File(rootDir, "shaderpacks").apply { mkdirs() }
    val savesDir: File get() = File(rootDir, "saves").apply { mkdirs() }
    val screenshotsDir: File get() = File(rootDir, "screenshots").apply { mkdirs() }
    val logsDir: File get() = File(rootDir, "logs").apply { mkdirs() }
    val crashReportsDir: File get() = File(rootDir, "crash-reports").apply { mkdirs() }
    val profilesDir: File get() = File(rootDir, "profiles").apply { mkdirs() }
    val skinsDir: File get() = File(rootDir, "skins").apply { mkdirs() }
    val nativesTempDir: File get() = File(rootDir, "natives-tmp").apply { mkdirs() }

    fun getSkinFile(uuid: String): File = File(skinsDir, "$uuid.png")

    fun getVersionDir(versionId: String): File = File(versionsDir, versionId).apply { mkdirs() }

    fun getVersionJsonFile(versionId: String): File = File(getVersionDir(versionId), "$versionId.json")

    fun getVersionJarFile(versionId: String): File = File(getVersionDir(versionId), "$versionId.jar")

    fun getNativesDir(versionId: String): File = File(getVersionDir(versionId), "natives").apply { mkdirs() }

    fun getAssetIndexFile(assetIndexId: String): File = File(assetIndexesDir, "$assetIndexId.json")

    fun getAssetObjectFile(hash: String): File {
        val prefix = hash.substring(0, 2.coerceAtMost(hash.length))
        val prefixDir = File(assetObjectsDir, prefix).apply { mkdirs() }
        return File(prefixDir, hash)
    }

    fun getAvailableStorageBytes(): Long {
        return try {
            val stat = StatFs(rootDir.path)
            stat.availableBlocksLong * stat.blockSizeLong
        } catch (e: Exception) {
            -1L
        }
    }

    fun getTotalStorageBytes(): Long {
        return try {
            val stat = StatFs(rootDir.path)
            stat.blockCountLong * stat.blockSizeLong
        } catch (e: Exception) {
            -1L
        }
    }

    fun formatBytes(bytes: Long): String {
        if (bytes < 0) return "Unknown"
        val mb = bytes.toDouble() / (1024 * 1024)
        val gb = mb / 1024
        return if (gb >= 1.0) {
            String.format("%.1f GB", gb)
        } else {
            String.format("%.1f MB", mb)
        }
    }

    fun cleanNativesTemp() {
        try {
            if (nativesTempDir.exists() && !nativesTempDir.deleteRecursively()) {
                throw IllegalStateException("Could not delete native temp directory: " + nativesTempDir.absolutePath)
            }
            nativesTempDir.mkdirs()
        } catch (e: Exception) {
            com.example.logs.LauncherLogger.warn("Native temp cleanup failed: " + e.message)
            throw e
        }
    }
}
