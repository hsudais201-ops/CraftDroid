package com.example.renderer

import android.app.ActivityManager
import android.content.Context
import android.os.Build

/** Device-adaptive performance policy. Keeps low-RAM devices from over-allocating
 * memory while giving capable devices more headroom. Users can still override RAM.
 */
data class PerformanceProfile(
    val tier: Tier,
    val recommendedRamMb: Int,
    val maxRamMb: Int,
    val targetFps: Int,
    val renderScale: Float,
    val aggressiveGc: Boolean
) {
    enum class Tier { LOW, BALANCED, HIGH }

    companion object {
        fun forTier(tier: Tier): PerformanceProfile = when (tier) {
            Tier.LOW -> PerformanceProfile(Tier.LOW, 768, 1024, 30, 0.70f, true)
            Tier.BALANCED -> PerformanceProfile(Tier.BALANCED, 1536, 3072, 60, 0.85f, false)
            Tier.HIGH -> PerformanceProfile(Tier.HIGH, 3072, 6144, 90, 1.0f, false)
        }

        fun detect(context: Context): PerformanceProfile {
            val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            val totalMb = am?.let {
                val info = ActivityManager.MemoryInfo()
                it.getMemoryInfo(info)
                (info.totalMem / (1024 * 1024)).toInt()
            } ?: 4096
            val lowRam = Build.VERSION.SDK_INT >= 19 && am?.isLowRamDevice == true
            return when {
                lowRam || totalMb <= 3072 -> forTier(Tier.LOW)
                totalMb <= 6144 -> forTier(Tier.BALANCED)
                else -> forTier(Tier.HIGH)
            }
        }
    }

    /** Safely caps a user-selected heap without starving Minecraft on low-memory devices. */
    fun clampRam(requestedMb: Int, availableMb: Int): Int {
        val safety = if (tier == Tier.LOW) 512 else 1024
        val minimum = if (tier == Tier.LOW) 512 else 768
        val availableCap = (availableMb - safety).coerceAtLeast(minimum)
        return requestedMb.coerceIn(minimum, minOf(maxRamMb, availableCap))
    }

    fun defaultJvmArgs(): String = buildString {
        if (aggressiveGc) {
            append("-XX:+UseSerialGC -XX:MaxGCPauseMillis=100")
        } else {
            append("-XX:+UseG1GC -XX:MaxGCPauseMillis=80")
        }
        if (!aggressiveGc) append(" -XX:+UseStringDeduplication")
    }
}
