package com.example.renderer

import com.example.logs.LauncherLogger
import java.io.File

/** Applies launcher performance defaults to Minecraft's options.txt.
 *
 * Only well-known graphics/performance keys are touched. Existing unrelated
 * options are preserved, and the file is updated atomically with a verified
 * copy fallback for filesystems where renameTo() is unavailable.
 */
object MinecraftPerformanceTuner {

    data class AppliedSettings(
        val maxFps: Int,
        val renderDistance: Int,
        val simulationDistance: Int,
        val graphics: String
    )

    fun apply(optionsFile: File, profile: PerformanceProfile, fpsCap: Int): AppliedSettings? {
        return try {
            optionsFile.parentFile?.mkdirs()
            val existing = if (optionsFile.isFile) optionsFile.readLines() else emptyList()
            val values = linkedMapOf<String, String>()
            val order = ArrayList<String>()
            val keyMarker = "\u0000"

            for (line in existing) {
                if (line.startsWith("#") || !line.contains(':')) {
                    order += line
                    continue
                }
                val key = line.substringBefore(':')
                if (!values.containsKey(key)) order += keyMarker + key
                values[key] = line.substringAfter(':')
            }

            val targetFps = fpsCap.coerceIn(30, profile.targetFps)
            val (renderDistance, simulationDistance, graphics, particles, clouds, entityShadows) = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> listOf(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> listOf(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> listOf(14, 8, "fancy", "all", "true", "true")
            }

            val tuned = linkedMapOf(
                "maxFps" to targetFps.toString(),
                "renderDistance" to renderDistance.toString(),
                "simulationDistance" to simulationDistance.toString(),
                "graphics" to graphics,
                "particles" to particles,
                "renderClouds" to clouds,
                "entityShadows" to entityShadows,
                "biomeBlendRadius" to if (profile.tier == PerformanceProfile.Tier.LOW) "0" else "2",
                "mipmapLevels" to if (profile.tier == PerformanceProfile.Tier.LOW) "0" else "2",
                "entityDistanceScaling" to if (profile.tier == PerformanceProfile.Tier.LOW) "0.5" else "0.75"
            )
            for ((key, value) in tuned) values[key] = value

            val output = ArrayList<String>(values.size + order.size)
            val emitted = HashSet<String>()
            for (entry in order) {
                if (entry.startsWith(keyMarker)) {
                    val key = entry.substring(keyMarker.length)
                    val value = values[key]
                    if (value != null) {
                        output += "$key:$value"
                        emitted += key
                    }
                } else {
                    output += entry
                }
            }
            for ((key, value) in values) {
                if (emitted.add(key)) output += "$key:$value"
            }

            val tmp = File(optionsFile.parentFile, optionsFile.name + ".droidtmp")
            tmp.writeText(output.joinToString("\n") + "\n")
            if (!tmp.isFile || tmp.length() <= 0L) {
                tmp.delete()
                throw IllegalStateException("Unable to prepare Minecraft options file")
            }

            if (optionsFile.exists() && !optionsFile.delete()) {
                tmp.delete()
                throw IllegalStateException("Unable to replace Minecraft options file")
            }
            if (!tmp.renameTo(optionsFile)) {
                tmp.inputStream().use { input ->
                    optionsFile.outputStream().use { outputStream ->
                        input.copyTo(outputStream, 64 * 1024)
                        outputStream.fd.sync()
                    }
                }
                tmp.delete()
            }
            if (!optionsFile.isFile || optionsFile.length() != tmp.length().takeIf { it > 0L } ?: optionsFile.length()) {
                if (!optionsFile.isFile || optionsFile.length() <= 0L) {
                    tmp.delete()
                    throw IllegalStateException("Unable to verify Minecraft options file")
                }
            }
            tmp.delete()

            AppliedSettings(targetFps, renderDistance, simulationDistance, graphics).also {
                LauncherLogger.info(
                    "Performance profile applied: tier=${profile.tier}, fps=${it.maxFps}, " +
                        "renderDistance=${it.renderDistance}, simulationDistance=${it.simulationDistance}, graphics=${it.graphics}"
                )
            }
        } catch (e: Exception) {
            LauncherLogger.warn("Could not apply automatic Minecraft performance settings: ${e.message}")
            null
        }
    }
}
