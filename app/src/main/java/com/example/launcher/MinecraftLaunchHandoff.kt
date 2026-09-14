package com.example.launcher

import android.content.Intent
import java.io.File

/** Immutable launch handoff decoded from the intent passed to the Minecraft runtime activity. */
data class MinecraftLaunchHandoff(
    val version: String,
    val mainClass: String,
    val classpath: List<File>,
    val assetIndex: String?,
    val nativeDir: File,
    val minecraftRoot: File,
    val valid: Boolean,
    val error: String? = null
)

object MinecraftLaunchHandoffReader {
    fun read(intent: Intent): MinecraftLaunchHandoff {
        val version = intent.getStringExtra("minecraft_version").orEmpty()
        val mainClass = intent.getStringExtra("minecraft_main_class").orEmpty()
        val classpathRaw = intent.getStringExtra("minecraft_classpath").orEmpty()
        val assetIndex = intent.getStringExtra("minecraft_asset_index")?.takeIf { it.isNotBlank() }
        val nativePath = intent.getStringExtra("minecraft_native_dir").orEmpty()
        val rootPath = intent.getStringExtra("minecraft_root").orEmpty()
        if (version.isBlank()) return invalid(version, "Minecraft version is missing")
        if (mainClass.isBlank()) return invalid(version, "Minecraft main class is missing")
        if (classpathRaw.isBlank()) return invalid(version, "Minecraft classpath is missing")
        if (nativePath.isBlank()) return invalid(version, "Minecraft native directory is missing")
        if (rootPath.isBlank()) return invalid(version, "Minecraft root is missing")

        val classpath = classpathRaw.split(File.pathSeparator)
            .filter { it.isNotBlank() }
            .map(::File)
        if (classpath.isEmpty()) return invalid(version, "Minecraft classpath is empty")
        if (classpath.any { !it.isFile || it.length() <= 0L }) {
            return invalid(version, "Minecraft classpath contains a missing artifact")
        }
        val nativeDir = File(nativePath)
        val root = File(rootPath)
        if (!nativeDir.isDirectory) return invalid(version, "Minecraft native directory is missing")
        if (!root.isDirectory) return invalid(version, "Minecraft root directory is missing")

        return MinecraftLaunchHandoff(version, mainClass, classpath, assetIndex, nativeDir, root, true)
    }

    private fun invalid(version: String, error: String) =
        MinecraftLaunchHandoff(version, "", emptyList(), null, File("."), File("."), false, error)
}
