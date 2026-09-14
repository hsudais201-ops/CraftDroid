package com.example.launcher

import android.content.Context
import java.io.File

/** Single source of truth for the Android-side Minecraft data directory. */
object MinecraftStorageResolver {
    private const val ROOT_NAME = "minecraft"
    private val VERSION_ID = Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

    fun root(context: Context): File =
        File(context.filesDir, ROOT_NAME).apply { mkdirs() }

    fun requireValidVersion(minecraftVersion: String): String =
        minecraftVersion.trim().also {
            require(VERSION_ID.matches(it)) { "Invalid Minecraft version id" }
        }

    fun version(context: Context, minecraftVersion: String): File {
        val safe = requireValidVersion(minecraftVersion)
        return File(root(context), "versions/$safe").apply { mkdirs() }
    }

    fun libraries(context: Context): File =
        File(root(context), "libraries").apply { mkdirs() }

    fun assets(context: Context): File =
        File(root(context), "assets").apply { mkdirs() }

    fun natives(context: Context, minecraftVersion: String): File =
        File(version(context, minecraftVersion), "natives").apply { mkdirs() }
}
