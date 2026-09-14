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
        val normalized = version.trim()
        val root = MinecraftStorageResolver.root(context)
        if (normalized.isBlank()) {
            val empty = File(root, "versions/invalid")
            return Result(normalized, root, empty, File(empty, "invalid.jar"), MinecraftStorageResolver.libraries(context), MinecraftStorageResolver.assets(context), File(empty, "natives"), false, "Minecraft version is empty")
        }
        if (!normalized.matches(Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"))) {
            val invalid = File(root, "versions/invalid")
            return Result(normalized, root, invalid, File(invalid, "invalid.jar"), MinecraftStorageResolver.libraries(context), MinecraftStorageResolver.assets(context), File(invalid, "natives"), false, "Invalid Minecraft version id")
        }

        val versionDir = MinecraftStorageResolver.version(context, normalized)
        val client = File(versionDir, "$normalized.jar")
        val libraries = MinecraftStorageResolver.libraries(context)
        val assets = MinecraftStorageResolver.assets(context)
        val natives = MinecraftStorageResolver.natives(context, normalized)
        return when {
            !File(versionDir, "$normalized.json").isFile -> Result(normalized, root, versionDir, client, libraries, assets, natives, false, "Version metadata is missing")
            !client.isFile || client.length() <= 0L -> Result(normalized, root, versionDir, client, libraries, assets, natives, false, "Minecraft client JAR is missing")
            !libraries.isDirectory -> Result(normalized, root, versionDir, client, libraries, assets, natives, false, "Minecraft libraries directory is missing")
            !assets.isDirectory -> Result(normalized, root, versionDir, client, libraries, assets, natives, false, "Minecraft assets directory is missing")
            else -> Result(normalized, root, versionDir, client, libraries, assets, natives, true)
        }
    }
}
