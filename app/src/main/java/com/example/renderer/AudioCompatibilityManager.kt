package com.example.renderer

import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import java.io.File

/**
 * Prepares OpenAL for Minecraft's LWJGL audio layer.
 *
 * Desktop LWJGL must not be allowed to pick a host OpenAL implementation on
 * Android. CraftDroid loads its Android OpenAL-Soft library first and exposes
 * the native directory through the standard LWJGL/OpenAL search properties.
 */
object AudioCompatibilityManager {
    data class Result(
        val enabled: Boolean,
        val openAl: File?,
        val reason: String
    )

    fun validate(version: VersionDetail, nativeDir: File): Result {
        val openAl = sequenceOf(
            File(nativeDir, "libopenal.so"),
            File(nativeDir, "libopenal_1.so")
        ).firstOrNull { it.isFile && it.length() > 0L }

        if (openAl == null) {
            return Result(false, null, "Android OpenAL native library is missing")
        }

        val hasAudioBinding = version.libraries.any {
            it.name == "org.lwjgl:lwjgl-openal" ||
                it.name.startsWith("org.lwjgl.lwjgl:lwjgl")
        }

        return if (hasAudioBinding) {
            Result(true, openAl, "LWJGL OpenAL binding detected; Android OpenAL selected")
        } else {
            // Some older/modified versions load audio through their bundled
            // native layer without an explicit modern lwjgl-openal coordinate.
            Result(true, openAl, "OpenAL native bridge available; no explicit LWJGL OpenAL coordinate")
        }
    }

    fun applyEnvironment(environment: MutableMap<String, String>, result: Result, nativeDir: File) {
        if (!result.enabled || result.openAl == null) return

        // OpenAL Soft uses this variable to select its Android backend where
        // supported. Keep the default flexible: if a packaged backend is not
        // present, OpenAL Soft can fall back instead of failing initialization.
        environment["ALSOFT_DRIVERS"] = ""
        environment["ALSOFT_LOGLEVEL"] = "0"
        environment["OPENAL_DEVICE"] = "Default"
        environment["OPENALSOFT_CONF"] = File(nativeDir, "alsoft.conf").absolutePath
        environment["CRAFTDROID_OPENAL"] = "android-openal-soft"
        environment["CRAFTDROID_OPENAL_LIBRARY"] = result.openAl.absolutePath

        LauncherLogger.info("Audio backend: ${result.reason}; ${result.openAl.name}")
    }
}
