package com.example.versions

/**
 * Authoritative Minecraft -> minimum Java major mapping used by both the
 * version browser and launch path.
 *
 * Legacy releases use 1.x.y numbering. Starting with 26.1, Mojang uses
 * year.release numbering (26.1, 26.2, ...).
 */
object MinecraftJavaRequirements {
    fun requiredMajor(versionId: String): Int {
        val normalized = versionId.trim().removePrefix("v")
        val parts = normalized.split('.', '-', '+').mapNotNull { it.toIntOrNull() }
        val first = parts.getOrNull(0) ?: 1
        val second = parts.getOrNull(1) ?: 0
        val patch = parts.getOrNull(2) ?: 0

        return when {
            first >= 26 -> 25
            first == 1 && second >= 21 -> 21
            first == 1 && second == 20 && patch >= 5 -> 21
            first == 1 && second in 18..20 -> 17
            first == 1 && second == 17 -> 16
            first == 1 && second <= 16 -> 8
            else -> 8
        }
    }

    fun isSupportedRequest(major: Int): Boolean = major in setOf(8, 16, 17, 21, 25)

    /**
     * CraftDroid ships Java 17 instead of a separate Android Java 16 image.
     * Java 17 is the deliberate compatibility runtime for the Java-16 era.
     */
    fun isCompatibleRuntime(requiredMajor: Int, actualMajor: Int): Boolean =
        actualMajor == requiredMajor || (requiredMajor == 16 && actualMajor == 17)
}
