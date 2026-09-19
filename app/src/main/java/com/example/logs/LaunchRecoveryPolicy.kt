package com.example.logs

import android.app.ActivityManager
import android.content.Context
import com.example.renderer.RendererBackend
import java.io.File

/**
 * Safe pre-launch recovery decisions. This never attempts to recover from a
 * live SIGSEGV; native crashes terminate the process. Instead, evidence from a
 * previous HotSpot crash is used to avoid immediately repeating the same path.
 */
object LaunchRecoveryPolicy {
    data class MemoryPlan(val maxRamMb: Int, val minRamMb: Int, val reason: String)

    fun memoryPlan(context: Context, requestedMb: Int): MemoryPlan {
        val info = ActivityManager.MemoryInfo()
        val am = context.getSystemService(ActivityManager::class.java)
        am?.getMemoryInfo(info)
        val availableMb = (info.availMem / (1024L * 1024L)).toInt().coerceAtLeast(512)
        val conservativeCap = (availableMb * 0.55f).toInt().coerceAtLeast(768)
        val maxRam = requestedMb.coerceIn(768, conservativeCap.coerceAtMost(4096))
        val minRam = (maxRam / 4).coerceIn(256, 768)
        val reason = "requested=${requestedMb}MB available=${availableMb}MB cap=${conservativeCap}MB selected=${maxRam}MB"
        LauncherLogger.info("Memory recovery plan: $reason")
        return MemoryPlan(maxRam, minRam, reason)
    }

    fun rendererFallbackFromPreviousCrash(rootDir: File, requested: RendererBackend): RendererBackend {
        val latest = rootDir.listFiles()?.filter { it.isFile && it.name.startsWith("hs_err_pid") && it.name.endsWith(".log") }?.maxByOrNull { it.lastModified() } ?: return requested
        val text = runCatching { latest.readText() }.getOrDefault("").lowercase()
        if (text.isBlank()) return requested

        val rendererCrash = listOf("libgl4es", "mobileglues", "libzink", "libvulkan", "glfw", "lwjgl", "egl").any { it in text }
        if (rendererCrash && requested != RendererBackend.COMPATIBILITY) {
            LauncherLogger.warn("Previous HotSpot native crash implicated graphics/native code (${latest.name}); using Compatibility renderer for this launch.")
            return RendererBackend.COMPATIBILITY
        }
        return requested
    }

    fun stripUnsafeMemoryOverrides(args: String): String {
        if (args.isBlank()) return ""
        return args.trim().split(Regex("\\s+"))
            .filterNot { it.startsWith("-Xmx", true) || it.startsWith("-Xms", true) }
            .joinToString(" ")
    }
}
