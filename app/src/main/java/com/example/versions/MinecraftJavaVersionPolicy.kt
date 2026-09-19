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
            Regex("""^26(?:\.|$)""").containsMatchIn(id) -> 25
            Regex("""^1\.21(?:\.|$)""").containsMatchIn(id) -> 21
            id == "1.20.5" || id == "1.20.6" || Regex("""^1\.2[01](?:\.|$)""").containsMatchIn(id) && id.startsWith("1.20.") && minorOf(id) >= 5 -> 21
            Regex("""^1\.2[01](?:\.|$)""").containsMatchIn(id) && id.startsWith("1.20.") -> 17
            Regex("""^1\.(18|19)(?:\.|$)""").containsMatchIn(id) -> 17
            Regex("""^1\.17(?:\.|$)""").containsMatchIn(id) -> 16
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
