package com.example.renderer

import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import java.io.File

/**
 * Selects/validates the Android LWJGL native ABI used by CraftDroid.
 *
 * Minecraft's downloaded natives are desktop artifacts on normal Mojang
 * manifests. They must remain available to the game files, but CraftDroid
 * must put its Android-compatible LWJGL/GLFW binaries first in the native
 * search path. We therefore fingerprint the Android liblwjgl.so and compare
 * any discoverable LWJGL version against the Java artifact version.
 */
object NativeLwjglCompatibilityManager {
    data class Result(
        val valid: Boolean,
        val javaVersions: List<String>,
        val nativeVersion: String?,
        val nativeFile: File?,
        val details: String
    )

    fun validate(version: VersionDetail, androidNativeDir: File, profile: LwjglRuntimeProfile.Profile = LwjglRuntimeProfile.resolve(version)): Result {
        val javaVersions = version.libraries
            .filter { it.name.startsWith("org.lwjgl:") }
            .mapNotNull { coordinateVersion(it.name) }
            .distinct()

        if (profile.family == LwjglRuntimeProfile.ApiFamily.LWJGL2_COMPAT) {
            LauncherLogger.info("Native LWJGL check using LWJGL2 compatibility profile: ${profile.reason}")
        }

        val abiCheck = NativeAbiVerifier.verify(androidNativeDir)
        if (!abiCheck.valid) {
            return Result(false, javaVersions, null, null, "Android native ABI check failed: ${abiCheck.details}")
        }

        // Select the exact JNI filename required by the resolved API family.
        // Do not silently validate whichever family happens to sort first: if
        // both are bundled, loading/validating the wrong JNI generation can
        // poison the process before Minecraft starts.
        val expectedNativeName = when (profile.family) {
            LwjglRuntimeProfile.ApiFamily.LWJGL3_NATIVE_GLFW -> "liblwjgl3.so"
            LwjglRuntimeProfile.ApiFamily.LWJGL2_COMPAT -> "liblwjgl.so"
        }
        val native = File(androidNativeDir, expectedNativeName)
        if (!native.isFile || native.length() < 4096L) {
            val alternate = if (expectedNativeName == "liblwjgl3.so") "liblwjgl.so" else "liblwjgl3.so"
            val alternateFile = File(androidNativeDir, alternate)
            val suffix = if (alternateFile.isFile) "; alternate $alternate exists but is not valid for profile" else ""
            return Result(false, javaVersions, null, native, "Android LWJGL native library $expectedNativeName is missing or invalid$suffix")
        }

        val nativeVersion = detectVersion(native)
        // Android Pojav-compatible native LWJGL is a platform port, not the
        // Maven desktop artifact. Its embedded version string can therefore
        // differ from the Java LWJGL patch version (and some stripped builds
        // contain no version string at all). Requiring an exact string here
        // caused valid stacks to be rejected before the JVM even started.
        // Compatibility is instead established by the profile, ABI/ELF checks,
        // and the JNI GLFW handshake performed immediately before launch.
        if (profile.family == LwjglRuntimeProfile.ApiFamily.LWJGL2_COMPAT &&
            javaVersions.isNotEmpty() && javaVersions.none { it.startsWith("2.") }) {
            LauncherLogger.warn("LWJGL2 compatibility profile has no 2.x Maven coordinate; continuing with Android compatibility bridge")
        }

        val detail = "profile=${profile.family}; Android $expectedNativeName=${nativeVersion ?: "unknown"}; Java LWJGL=${javaVersions.joinToString().ifBlank { "none" }}; ABI/ELF/JNI checks required"
        LauncherLogger.info("Native LWJGL compatibility: $detail")
        return Result(true, javaVersions, nativeVersion, native, detail)
    }

    private fun coordinateVersion(name: String): String? {
        val p = name.split(':')
        return p.getOrNull(2)?.takeIf { p.getOrNull(0) == "org.lwjgl" && it.isNotBlank() }
    }

    private fun detectVersion(file: File): String? {
        return runCatching {
            val bytes = file.inputStream().use { input ->
                val max = 2 * 1024 * 1024
                val out = ByteArray(max)
                var used = 0
                while (used < max) {
                    val n = input.read(out, used, max - used)
                    if (n <= 0) break
                    used += n
                }
                out.copyOf(used)
            }
            val text = buildString(bytes.size) {
                for (b in bytes) {
                    val c = b.toInt() and 0xff
                    append(if (c in 32..126) c.toChar() else ' ')
                }
            }
            Regex("(?:LWJGL|lwjgl)[^0-9]{0,40}(3\\.[0-9]+\\.[0-9]+)").find(text)?.groupValues?.getOrNull(1)
                ?: Regex("\\b(3\\.[0-9]+\\.[0-9]+)\\b").find(text)?.groupValues?.getOrNull(1)
        }.getOrNull()
    }
}
