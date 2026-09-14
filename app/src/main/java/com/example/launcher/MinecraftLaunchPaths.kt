package com.example.launcher

import android.content.Context
import java.io.File

/** Resolved filesystem locations for one installed Minecraft version. */
object MinecraftLaunchPaths {
    data class Result(
        val version: String,
        val minecraftRoot: File,
        val versionDir: File,
        val clientJar: File,
        val librariesDir: File,
        val assetsDir: File,
        val nativesDir: File,
        val valid: Boolean,
        val error: String? = null
    )

    fun resolve(context: Context, version: String): Result {
        val root = MinecraftStorageResolver.root(context)
        val versionDir = MinecraftStorageResolver.version(context, version)
        val client = File(versionDir, "$version.jar")
        val libraries = MinecraftStorageResolver.libraries(context)
        val assets = MinecraftStorageResolver.assets(context)
        val natives = MinecraftStorageResolver.natives(context, version)
        return when {
            version.isBlank() -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft version is empty")
            !File(versionDir, "$version.json").isFile -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Version metadata is missing")
            !client.isFile || client.length() <= 0L -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft client JAR is missing")
            !libraries.isDirectory -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft libraries directory is missing")
            !assets.isDirectory -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft assets directory is missing")
            else -> Result(version, root, versionDir, client, libraries, assets, natives, true)
        }
    }
}
