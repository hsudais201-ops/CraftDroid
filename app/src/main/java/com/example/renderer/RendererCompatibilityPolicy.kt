package com.example.renderer

import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail

/**
 * Decides which Android renderer is safe for a Minecraft version and device.
 * The policy is conservative and now also validates that the selected native
 * backend actually exists in the installed Android runtime stack.
 */
object RendererCompatibilityPolicy {
    data class Decision(
        val requested: RendererBackend,
        val effective: RendererBackend,
        val allowed: Boolean,
        val reason: String
    )

    private fun isModernMinecraft(id: String): Boolean {
        val m = Regex("^(?:1\\.)(\\d+)(?:\\.\\d+)?").find(id) ?: return true
        return (m.groupValues[1].toIntOrNull() ?: 21) >= 17
    }

    fun choose(
        requested: RendererBackend,
        gpu: DeviceGpuInfo,
        version: VersionDetail
    ): Decision {
        val modern = isModernMinecraft(version.id)
        val lwjgl3 = version.libraries.any { it.name == "org.lwjgl:lwjgl" }
        val effectiveRequested = if (requested == RendererBackend.AUTO) gpu.recommendedBackend else requested

        if (!gpu.isSupported) {
            return Decision(requested, RendererBackend.COMPATIBILITY, true,
                "Device ABI/Android support is limited; using compatibility renderer")
        }

        return when (effectiveRequested) {
            RendererBackend.ZINK -> {
                if (!gpu.hasVulkan12) {
                    Decision(requested, RendererBackend.GL4ES, true,
                        "Zink requested but Vulkan 1.2 is unavailable; falling back to GL4ES")
                } else if (!modern) {
                    Decision(requested, RendererBackend.GL4ES, true,
                        "Zink is disabled for pre-1.17 versions in the conservative policy")
                } else {
                    Decision(requested, RendererBackend.ZINK, true,
                        "Vulkan is available and the selected Minecraft version is modern")
                }
            }
            RendererBackend.MOBILEGLUES -> {
                if (!modern || !lwjgl3) {
                    Decision(requested, RendererBackend.GL4ES, true,
                        "MobileGlues is intended for modern LWJGL3 Minecraft; using GL4ES fallback")
                } else if (gpu.glEsVersion.substringBefore('.').toIntOrNull() ?: 2 < 3) {
                    Decision(requested, RendererBackend.GL4ES, true,
                        "MobileGlues requires GLES 3-capable hardware; using GL4ES")
                } else {
                    Decision(requested, RendererBackend.MOBILEGLUES, true,
                        "Modern LWJGL3 + GLES3 device")
                }
            }
            RendererBackend.COMPATIBILITY -> Decision(requested, RendererBackend.COMPATIBILITY, true,
                "Compatibility renderer explicitly selected")
            RendererBackend.GL4ES -> Decision(requested, RendererBackend.GL4ES, true,
                "GL4ES is the broad Android OpenGL compatibility fallback")
            RendererBackend.AUTO -> error("AUTO must be resolved before policy evaluation")
        }.also {
            LauncherLogger.info("Renderer policy: requested=${it.requested.title}, effective=${it.effective.title}, reason=${it.reason}")
        }
    }

    /**
     * Final installed-stack gate. This prevents selecting a backend whose
     * native implementation is absent even when the device itself supports it.
     */
    fun validateInstalledBackend(
        backend: RendererBackend,
        stack: NativeComponentManager.NativeStack,
        gpu: DeviceGpuInfo
    ): Decision {
        fun fallback(reason: String): Decision = Decision(backend, RendererBackend.GL4ES, true, reason)
        return when (backend) {
            RendererBackend.GL4ES -> if (stack.hasGl4es) {
                Decision(backend, backend, true, "GL4ES native backend is installed")
            } else {
                Decision(backend, backend, false, "GL4ES native backend is missing")
            }
            RendererBackend.MOBILEGLUES -> if (stack.hasMobileGlues && (gpu.glEsVersion.substringBefore('.').toIntOrNull() ?: 2) >= 3) {
                Decision(backend, backend, true, "MobileGlues native backend is installed and GLES3 is available")
            } else {
                fallback("MobileGlues native backend is unavailable on the installed device stack")
            }
            RendererBackend.ZINK -> if (stack.hasZink && gpu.hasVulkan12) {
                Decision(backend, backend, true, "Zink/Mesa native backend is installed and Vulkan 1.2 is available")
            } else {
                fallback("Zink native backend or Vulkan 1.2 support is unavailable; using GL4ES")
            }
            RendererBackend.COMPATIBILITY -> Decision(backend, backend, true, "Compatibility mode does not require a third-party renderer")
            RendererBackend.AUTO -> error("AUTO must be resolved before installed-backend validation")
        }
    }
}
