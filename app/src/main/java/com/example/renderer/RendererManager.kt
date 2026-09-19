package com.example.renderer

import android.app.ActivityManager
import android.content.Context
import android.content.pm.PackageManager
import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLDisplay
import android.opengl.GLES20
import android.os.Build
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import java.io.File

enum class RendererBackend(val title: String, val description: String) {
    AUTO("Auto", "Automatically selects the best renderer based on GPU capabilities"),
    GL4ES("GL4ES (OpenGL 2.1)", "Fast OpenGL-to-OpenGLES translation layer for Adreno/Mali/PowerVR"),
    MOBILEGLUES("MobileGlues (OpenGL ES 3)", "Modern OpenGL compatibility layer on top of Android OpenGL ES 3.x"),
    ZINK("Zink (OpenGL via Vulkan)", "Translates modern OpenGL 3.3/4.6 calls through Vulkan drivers"),
    COMPATIBILITY("Compatibility Mode", "Software/safe fallback mode for older devices and driver workarounds")
}

data class DeviceGpuInfo(
    val glEsVersion: String,
    val glRenderer: String,
    val glVendor: String,
    val glVersion: String,
    val hasVulkan: Boolean,
    val cpuAbi: String,
    val androidVersion: Int,
    val isSupported: Boolean,
    val recommendedBackend: RendererBackend
)

class RendererManager(private val context: Context, private val fileSystem: MinecraftFileSystem? = null, private val nativeComponentManager: NativeComponentManager? = null) {

    val gpuInfo: DeviceGpuInfo by lazy {
        detectCapabilities()
    }

    private fun detectCapabilities(): DeviceGpuInfo {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
        val glesVer = am?.deviceConfigurationInfo?.glEsVersion ?: "Unknown"

        val hasVulkan = context.packageManager.hasSystemFeature(PackageManager.FEATURE_VULKAN_HARDWARE_LEVEL)
        val abi = Build.SUPPORTED_ABIS.firstOrNull() ?: "Unknown"
        val sdk = Build.VERSION.SDK_INT

        // Probe EGL context to inspect real renderer and vendor
        var probedRenderer = Build.HARDWARE ?: "Unknown GPU"
        var probedVendor = Build.MANUFACTURER ?: "Unknown Vendor"
        var probedVersion = "OpenGL ES $glesVer"

        try {
            val display: EGLDisplay = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
            val version = IntArray(2)
            EGL14.eglInitialize(display, version, 0, version, 1)

            val attribList = intArrayOf(
                EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL14.EGL_NONE
            )
            val configs = arrayOfNulls<EGLConfig>(1)
            val numConfigs = IntArray(1)
            EGL14.eglChooseConfig(display, attribList, 0, configs, 0, 1, numConfigs, 0)

            if (numConfigs[0] > 0) {
                val contextAttribs = intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE)
                val eglCtx: EGLContext = EGL14.eglCreateContext(display, configs[0], EGL14.EGL_NO_CONTEXT, contextAttribs, 0)
                if (eglCtx != EGL14.EGL_NO_CONTEXT) {
                    val pbufferAttribs = intArrayOf(EGL14.EGL_WIDTH, 1, EGL14.EGL_HEIGHT, 1, EGL14.EGL_NONE)
                    val pbuffer = EGL14.eglCreatePbufferSurface(display, configs[0], pbufferAttribs, 0)
                    EGL14.eglMakeCurrent(display, pbuffer, pbuffer, eglCtx)

                    probedRenderer = GLES20.glGetString(GLES20.GL_RENDERER) ?: probedRenderer
                    probedVendor = GLES20.glGetString(GLES20.GL_VENDOR) ?: probedVendor
                    probedVersion = GLES20.glGetString(GLES20.GL_VERSION) ?: probedVersion

                    EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
                    EGL14.eglDestroySurface(display, pbuffer)
                    EGL14.eglDestroyContext(display, eglCtx)
                }
            }
            EGL14.eglTerminate(display)
        } catch (e: Exception) {
            LauncherLogger.warn("EGL probe warning: ${e.message}")
        }

        val isSupported = sdk >= 24 && (abi.contains("arm64") || abi.contains("x86_64") || abi.contains("armeabi"))
        val glesMajor = glesVer.substringBefore(".").toIntOrNull() ?: 2
        val recommended = when {
            hasVulkan && glesMajor < 3 && isSupported -> RendererBackend.ZINK
            glesMajor >= 3 && isSupported -> RendererBackend.MOBILEGLUES
            isSupported -> RendererBackend.GL4ES
            else -> RendererBackend.COMPATIBILITY
        }

        return DeviceGpuInfo(
            glEsVersion = glesVer,
            glRenderer = probedRenderer,
            glVendor = probedVendor,
            glVersion = probedVersion,
            hasVulkan = hasVulkan,
            cpuAbi = abi,
            androidVersion = sdk,
            isSupported = isSupported,
            recommendedBackend = recommended
        )
    }

    suspend fun ensureNativeStack(requiredLwjglVersion: String? = null, onStatus: (String) -> Unit): NativeComponentManager.NativeStack {
        val manager = nativeComponentManager
            ?: throw IllegalStateException("Native component manager is not configured")
        return manager.ensureInstalled(onStatus, requiredLwjglVersion)
    }

    /**
     * Builds environment variables and system properties needed by native LWJGL and graphics bridges.
     */
    fun buildRendererEnv(backend: RendererBackend, nativesDir: File): Map<String, String> {
        val env = mutableMapOf<String, String>()
        val effective = if (backend == RendererBackend.AUTO) gpuInfo.recommendedBackend else backend

        when (effective) {
            RendererBackend.GL4ES -> {
                env["LIBGL_ES"] = "2"
                env["LIBGL_GL"] = "21"
                env["LIBGL_MIPMAP"] = "3"
                env["LIBGL_USEVBO"] = "1"
                env["LIBGL_NOBANNER"] = "1"
                env["POJAV_RENDERER"] = "opengles2"
                env["LIBGL_EGL"] = "libgl4es_114.so"
                env["POJAVEXEC_EGL"] = "libgl4es_114.so"
            }
            RendererBackend.MOBILEGLUES -> {
                env["POJAV_RENDERER"] = "opengles_mobileglues"
                env["LIBGL_ES"] = "2"
                env["LIBGL_EGL"] = "libmobileglues.so"
                env["POJAVEXEC_EGL"] = "libmobileglues.so"
                env["MG_DIR_PATH"] = File(nativesDir, "MobileGlues").absolutePath
                env["LIBGL_MIPMAP"] = "3"
                env["LIBGL_NOERROR"] = "1"
                env["LIBGL_NOINTOVLHACK"] = "1"
                env["LIBGL_NORMALIZE"] = "1"
            }
            RendererBackend.ZINK -> {
                env["MESA_LOADER_DRIVER_OVERRIDE"] = "zink"
                env["MESA_VK_WSI_PRESENT_MODE"] = "fifo"
                env["GALLIUM_DRIVER"] = "zink"
                // Do not hard-code a vendor ICD path. Android devices expose
                // Vulkan drivers differently, and an invalid path can prevent
                // the JVM from starting before Minecraft even initializes.
                env["POJAV_RENDERER"] = "vulkan_zink"
                env["POJAV_VSYNC_IN_ZINK"] = "1"
                env["VTEST_SOCKET_NAME"] = File(nativesDir.parentFile, ".virgl_test").absolutePath
            }
            RendererBackend.COMPATIBILITY -> {
                env["LIBGL_ES"] = "2"
                env["LIBGL_GL"] = "14"
                env["LIBGL_NOBANNER"] = "1"
                env["LIBGL_BATCH"] = "1"
                env["POJAV_RENDERER"] = "opengles2"
            }
            RendererBackend.AUTO -> {}
        }

        // Only Android-compatible renderer libraries belong in the native linker path.
        // nativesDir is Minecraft's extracted desktop-native archive and must not be
        // exposed here; doing so can select liblwjgl/libopenal built for desktop Linux.
        val existingLd = System.getenv("LD_LIBRARY_PATH") ?: ""
        val rendererDir = fileSystem?.rendererDir?.absolutePath
        val extra = listOfNotNull(rendererDir).joinToString(File.pathSeparator)
        env["LD_LIBRARY_PATH"] = listOfNotNull(
            extra.takeIf { it.isNotBlank() },
            existingLd.takeIf { it.isNotBlank() },
            "/vendor/lib64",
            "/system/lib64"
        ).joinToString(File.pathSeparator)
        env["TMPDIR"] = File(fileSystem?.rootDir ?: context.cacheDir, "tmp").apply { mkdirs() }.absolutePath
        env["MESA_GLSL_CACHE_DIR"] = context.cacheDir.absolutePath
        env["POJAV_NATIVEDIR"] = nativesDir.absolutePath
        env["DRIVER_PATH"] = rendererDir ?: nativesDir.absolutePath
        env["AWTSTUB_WIDTH"] = context.resources.displayMetrics.widthPixels.toString()
        env["AWTSTUB_HEIGHT"] = context.resources.displayMetrics.heightPixels.toString()
        env["FORCE_VSYNC"] = "true"
        env["LIBGL_NOERROR"] = "1"
        env["LIBGL_NOINTOVLHACK"] = "1"
        env["LIBGL_NORMALIZE"] = "1"
        env["force_glsl_extensions_warn"] = "true"
        env["allow_higher_compat_version"] = "true"
        env["allow_glsl_extension_directive_midshader"] = "true"
        if (effective == RendererBackend.ZINK) env["POJAV_VSYNC_IN_ZINK"] = "1"
        return env
    }
}
