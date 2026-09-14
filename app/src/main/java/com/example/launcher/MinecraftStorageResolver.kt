package com.example.launcher

import android.content.Context
import java.io.File

/** Single source of truth for the Android-side Minecraft data directory. */
object MinecraftStorageResolver {
    private const val ROOT_NAME = "minecraft"

    fun root(context: Context): File =
        File(context.filesDir, ROOT_NAME).apply { mkdirs() }

    fun version(context: Context, minecraftVersion: String): File =
        File(root(context), "versions/$minecraftVersion").apply { mkdirs() }

    fun libraries(context: Context): File =
        File(root(context), "libraries").apply { mkdirs() }

    fun assets(context: Context): File =
        File(root(context), "assets").apply { mkdirs() }

    fun natives(context: Context, minecraftVersion: String): File =
        File(version(context, minecraftVersion), "natives").apply { mkdirs() }
}
