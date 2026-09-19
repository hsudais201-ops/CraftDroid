package com.example.versions

/**
 * Minecraft-to-Java compatibility policy.
 *
 * Prefer the explicit javaVersion.majorVersion from a version JSON when it is
 * present; this policy is the safe fallback for manifests/legacy profiles that
 * omit it. The 2026 year-drop releases (26.x) require Java 25.
 */
object MinecraftJavaVersionPolicy {
    fun requiredMajor(versionId: String): Int {
        val id = versionId.trim().lowercase()
        return when {
            id == "26" || id.startsWith("26.") -> 25
            id == "1.21" || id.startsWith("1.21.") -> 21
            id.startsWith("1.20.") && minorOf(id) >= 5 -> 21
            id == "1.20" || id.startsWith("1.20.") -> 17
            id == "1.18" || id.startsWith("1.18.") || id == "1.19" || id.startsWith("1.19.") -> 17
            id == "1.17" || id.startsWith("1.17.") -> 16
            else -> 8
        }
    }

    fun compatibleRuntimeMajor(requiredMajor: Int): Int {
        return when (requiredMajor) {
            16 -> 17
            8, 17, 21, 25 -> requiredMajor
            else -> error("Unsupported Minecraft Java requirement: $requiredMajor")
        }
    }

    private fun minorOf(id: String): Int {
        val parts = id.removePrefix("1.20.").split('.')
        return parts.firstOrNull()?.toIntOrNull() ?: -1
    }
}
