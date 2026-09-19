package com.example.renderer

import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail

/** Selects the Android LWJGL compatibility strategy for a Minecraft version. */
object LwjglRuntimeProfile {
    enum class ApiFamily { LWJGL2_COMPAT, LWJGL3_NATIVE_GLFW }

    data class Profile(
        val family: ApiFamily,
        val minecraftVersion: String,
        val javaVersions: List<String>,
        val requiresGlfwStub: Boolean,
        val requiresLwjglx: Boolean,
        val reason: String
    )

    fun resolve(version: VersionDetail): Profile {
        val versions = version.libraries
            .filter { it.name.startsWith("org.lwjgl:") }
            .mapNotNull { it.name.split(':').getOrNull(2) }
            .distinct()

        val legacyMarker = version.libraries.any {
            it.name.contains("lwjglx", ignoreCase = true) ||
                it.name.contains("lwjgl2", ignoreCase = true)
        }
        val legacyMinecraft = isOlderThan113(version.id)
        val family = if (legacyMinecraft || legacyMarker) ApiFamily.LWJGL2_COMPAT else ApiFamily.LWJGL3_NATIVE_GLFW

        val profile = Profile(
            family = family,
            minecraftVersion = version.id,
            javaVersions = versions,
            requiresGlfwStub = false,
            requiresLwjglx = family == ApiFamily.LWJGL2_COMPAT,
            reason = if (family == ApiFamily.LWJGL2_COMPAT)
                "Minecraft ${version.id} is pre-1.13 or declares LWJGL2 compatibility"
            else
                "Minecraft ${version.id} uses LWJGL3 with the current native GLFW backend; no Java GLFW stub is injected"
        )
        LauncherLogger.info("LWJGL runtime profile: ${profile.family}; ${profile.reason}; Java=${versions.joinToString()}")
        return profile
    }

    private fun isOlderThan113(id: String): Boolean {
        val match = Regex("^(\\d+)\\.(\\d+)(?:\\.(\\d+))?").find(id) ?: return false
        val major = match.groupValues[1].toIntOrNull() ?: return false
        val minor = match.groupValues[2].toIntOrNull() ?: return false
        return major == 1 && minor <= 12
    }
}
