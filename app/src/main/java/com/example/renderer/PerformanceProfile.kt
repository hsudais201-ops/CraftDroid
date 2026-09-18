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
            Tier.LOW -> PerformanceProfile(Tier.LOW, 640, 1024, 30, 0.70f, true)
            Tier.BALANCED -> PerformanceProfile(Tier.BALANCED, 1280, 2048, 60, 0.85f, false)
            Tier.HIGH -> PerformanceProfile(Tier.HIGH, 2048, 4096, 90, 1.0f, false)
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
        val preferredMinimum = if (tier == Tier.LOW) 640 else 768
        val emergencyMinimum = 384
        val availableAfterReserve = availableMb - safety

        // Never produce an invalid range when Android reports very little free
        // memory. Prefer a conservative emergency cap rather than silently
        // increasing the requested heap above what the device can currently spare.
        if (availableAfterReserve < emergencyMinimum) return emergencyMinimum
        val upper = minOf(maxRamMb, availableAfterReserve)
        val lower = minOf(preferredMinimum, upper)
        return requestedMb.coerceIn(lower, upper)
    }



    fun totalRamMb(context: Context): Int {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            ?: return 4096
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        return (info.totalMem / (1024L * 1024L)).toInt().coerceAtLeast(768)
    }

    fun availableRamMb(context: Context): Int {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
            ?: return 0
        val info = ActivityManager.MemoryInfo()
        am.getMemoryInfo(info)
        return (info.availMem / (1024L * 1024L)).toInt().coerceAtLeast(0)
    }

    /**
     * Produces a launch-time heap cap using both the device profile and current
     * available memory. The cap always leaves an Android-side reserve.
     */
    private fun deviceHeapCeilingMb(context: Context, profile: PerformanceProfile): Int {
        val total = totalRamMb(context)
        val deviceCap = when {
            total <= 2048 -> 768
            total <= 3072 -> 1024
            total <= 4096 -> 1536
            total <= 6144 -> 1792
            else -> profile.maxRamMb
        }
        return minOf(profile.maxRamMb, deviceCap)
    }

    fun safeRamMb(context: Context, requestedMb: Int): Int {
        val profile = detect(context)
        val minimum = when (profile.tier) {
            Tier.LOW -> 640
            Tier.BALANCED -> 768
            Tier.HIGH -> 1024
        }
        val reserve = when (profile.tier) {
            Tier.LOW -> 512
            Tier.BALANCED -> 768
            Tier.HIGH -> 1024
        }
        val dynamicCap = (availableRamMb(context) - reserve).coerceAtLeast(minimum)
        val deviceCap = deviceHeapCeilingMb(context, profile)
        val upper = minOf(deviceCap, dynamicCap.coerceAtLeast(minimum))
        return requestedMb.coerceIn(minimum, upper)
    }

    fun recommendedRamMb(context: Context): Int =
        safeRamMb(context, detect(context).recommendedRamMb)

    fun defaultJvmArgs(heapMb: Int): String {
        val safeHeap = heapMb.coerceAtLeast(128)
        return buildString {
            append("-Xms128m -Xmx").append(safeHeap).append("m ")
            append(defaultJvmArgs())
        }
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
