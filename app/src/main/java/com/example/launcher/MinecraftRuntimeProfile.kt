package com.example.launcher

/**
 * Minecraft Java runtime compatibility policy.
 *
 * Minecraft 26.1+ requires Java 25. Older releases retain their historically
 * compatible runtimes so existing installations are not broken by an upgrade.
 */
object MinecraftRuntimeProfile {
    data class Profile(
        val requiredJava: Int,
        val reason: String
    )

    fun forMinecraftVersion(version: String): Profile {
        val normalized = version.trim().removePrefix("v")
        val numeric = normalized.split('.', '-', '+').mapNotNull { it.toIntOrNull() }
        val first = numeric.getOrNull(0) ?: 1
        val second = numeric.getOrNull(1) ?: 0
        val patch = numeric.getOrNull(2) ?: 0

        return when {
            first >= 26 -> Profile(25, "Minecraft 26.x+ requires Java 25")
            first == 1 && second >= 21 && patch >= 6 -> Profile(21, "Modern 1.21.x runtime")
            first == 1 && second >= 21 -> Profile(21, "Minecraft 1.21 runtime")
            first == 1 && second >= 17 -> Profile(17, "Minecraft 1.17–1.20 runtime")
            first == 1 && second >= 16 -> Profile(8, "Minecraft 1.16 legacy runtime")
            first == 1 && second >= 13 -> Profile(8, "Minecraft 1.13–1.15 legacy runtime")
            else -> Profile(8, "Legacy Minecraft runtime")
        }
    }

    fun isSupportedJava(major: Int): Boolean = major in setOf(8, 16, 17, 21, 25)

    fun requiresJava25(version: String): Boolean = forMinecraftVersion(version).requiredJava == 25
}
