package com.example.launcher

import android.content.Context
import java.io.File

/** Security and consistency checks for launch data crossing the activity boundary. */
object MinecraftLaunchHandoffValidator {
    fun validate(context: Context, handoff: MinecraftLaunchHandoff): String? {
        if (!handoff.valid) return handoff.error ?: "Minecraft launch handoff is invalid"
        if (handoff.version.isBlank()) return "Minecraft version is missing"
        if (handoff.mainClass.isBlank()) return "Minecraft main class is missing"

        val root = MinecraftStorageResolver.root(context).canonicalFile
        val handoffRoot = handoff.minecraftRoot.canonicalFile
        if (handoffRoot != root) return "Minecraft root does not match launcher storage root"

        val versionDir = MinecraftStorageResolver.version(context, handoff.version).canonicalFile
        val clientJar = File(versionDir, "${handoff.version}.jar").canonicalFile
        if (!versionDir.isDirectory) return "Minecraft version directory is missing"
        if (!clientJar.isFile || clientJar.length() <= 0L) return "Minecraft client JAR is missing"

        val libraries = MinecraftStorageResolver.libraries(context).canonicalFile
        val assets = MinecraftStorageResolver.assets(context).canonicalFile
        val natives = MinecraftStorageResolver.natives(context, handoff.version).canonicalFile
        if (handoff.nativeDir.canonicalFile != natives) return "Minecraft native directory does not match selected version"
        if (!assets.isDirectory) return "Minecraft assets directory is missing"
        if (!libraries.isDirectory) return "Minecraft libraries directory is missing"
        if (!natives.isDirectory) return "Minecraft native directory is missing"

        fun inside(file: File, parent: File): Boolean {
            val child = file.canonicalFile.toPath()
            val base = parent.canonicalFile.toPath()
            return child == base || child.startsWith(base)
        }

        if (!inside(clientJar, versionDir)) return "Minecraft client path escapes version directory"
        if (handoff.classpath.any { !inside(it, libraries) && it.canonicalFile != clientJar }) {
            return "Minecraft classpath contains a path outside the launcher libraries"
        }
        if (handoff.classpath.none { it.canonicalFile == clientJar }) return "Minecraft classpath does not contain the client JAR"
        return null
    }
}
