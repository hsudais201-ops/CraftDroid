package com.example.game

import android.view.Surface
import java.io.File
import com.example.logs.LauncherLogger

/** Android -> native bridge used by the CraftDroid GLFW adapter. */
object NativeGameBridge {
    @Volatile private var loaded = false

    init {
        try {
            System.loadLibrary("craftdroidbridge")
            loaded = true
        } catch (t: Throwable) {
            LauncherLogger.warn("CraftDroid JNI bridge unavailable: ${t.message}")
        }
    }

    fun loadNativeStack(directory: File, preferLwjgl3: Boolean = true) {
        if (!loaded) return
        // The order matters: renderer/audio/exithook first, then the Pojav
        // execution layer, then GLFW, and finally LWJGL. Every library is
        // loaded RTLD_GLOBAL so JNI/native dependencies can resolve across
        // the stack exactly like a Pojav-style runtime.
        val order = if (preferLwjgl3) {
            listOf(
                "gl4es", "mobileglues", "openal", "c++_shared", "exithook",
                "pojavexec_awt", "pojavexec", "glfw", "lwjgl3"
            )
        } else {
            listOf(
                "gl4es", "mobileglues", "openal", "c++_shared", "exithook",
                "pojavexec_awt", "pojavexec", "glfw", "lwjgl"
            )
        }
        LauncherLogger.info("Loading Android native runtime from ${directory.absolutePath}")
        val files = directory.listFiles()
            ?.filter { it.isFile && it.name.endsWith(".so", true) }
            ?.sortedBy { it.name }
            .orEmpty()
        val remaining = files.toMutableList()
        var loadedCount = 0

        // Never let the generic dependency pass load the alternate LWJGL JNI
        // family. It must be excluded before any RTLD_GLOBAL load occurs.
        val selectedLwjglName = if (preferLwjgl3) "liblwjgl3.so" else "liblwjgl.so"
        val alternateLwjglName = if (preferLwjgl3) "liblwjgl.so" else "liblwjgl3.so"
        val alternates = remaining.filter {
            it.name.equals(alternateLwjglName, ignoreCase = true)
        }
        if (alternates.isNotEmpty()) {
            LauncherLogger.info("Skipping alternate LWJGL JNI library before dependency scan for selected $selectedLwjglName mode: ${alternates.joinToString { it.name }}")
            remaining.removeAll(alternates)
        }

        val selectedPresent = remaining.any { it.name.equals(selectedLwjglName, ignoreCase = true) }
        if (!selectedPresent) {
            LauncherLogger.warn("Selected LWJGL JNI library $selectedLwjglName is not bundled; native validation may fail")
        }

        // GLFW has the same two common Android-facing filenames as LWJGL.
        // Pick exactly one before any RTLD_GLOBAL dependency scan so the
        // alternate implementation can never become the process-wide GLFW
        // handle by accident. Prefer the canonical libglfw.so when present.
        val glfwCandidates = listOf("libglfw.so", "libglfw3.so")
        val selectedGlfwName = glfwCandidates.firstOrNull { name ->
            remaining.any { it.name.equals(name, ignoreCase = true) }
        }
        val alternateGlfwNames = glfwCandidates.filter { it != selectedGlfwName }
        if (selectedGlfwName != null) {
            LauncherLogger.info("Selected GLFW native library: $selectedGlfwName")
            val alternateGlfw = remaining.filter { file ->
                alternateGlfwNames.any { it.equals(file.name, ignoreCase = true) }
            }
            if (alternateGlfw.isNotEmpty()) {
                LauncherLogger.info("Skipping alternate GLFW library before dependency scan: ${alternateGlfw.joinToString { it.name }}")
                remaining.removeAll(alternateGlfw)
            }
        } else {
            LauncherLogger.warn("No supported GLFW native library (libglfw.so/libglfw3.so) is bundled")
        }

        // Load core components first. Matching by stem instead of an exact
        // filename handles upstream names such as libglfw3.so and versioned
        // OpenAL/GL4ES filenames.
        for (stem in order) {
            val match = remaining.firstOrNull {
                it.name.removePrefix("lib").startsWith(stem, ignoreCase = true)
            } ?: continue
            if (nativeLoadLibrary(match.absolutePath)) {
                loadedCount++
                LauncherLogger.info("Loaded native ${match.name}")
                remaining.remove(match)
            } else {
                LauncherLogger.warn("Could not load ${match.name}; continuing dependency scan")
            }
        }

        // Some Pojav/Mesa releases ship additional dependency .so files
        // (for example libc++_shared or helper libraries) with names that are
        // not stable across releases. Try the remaining bundled libraries so
        // DT_NEEDED dependencies are present before LWJGL starts. A failed
        // optional helper is logged but is not itself fatal; the final native
        // validation below remains the gate for GLFW/LWJGL.
        var progress: Boolean
        do {
            progress = false
            val pass = remaining.toList()
            for (file in pass) {
                if (nativeLoadLibrary(file.absolutePath)) {
                    loadedCount++
                    LauncherLogger.info("Loaded dependency native ${file.name}")
                    remaining.remove(file)
                    progress = true
                }
            }
        } while (progress && remaining.isNotEmpty())

        if (remaining.isNotEmpty()) {
            LauncherLogger.warn("Native dependency scan left ${remaining.size} optional/unloadable libraries: ${remaining.joinToString { it.name }}")
        }
        val diagnostics = nativeValidateNativeStack(directory.absolutePath, preferLwjgl3, selectedGlfwName)
        LauncherLogger.info("Native GLFW/LWJGL diagnostics: $diagnostics (loaded=$loadedCount)")
        if (diagnostics.contains("FAIL")) {
            throw IllegalStateException("Android native GLFW/LWJGL stack failed validation: $diagnostics")
        }
        val dependencyCheck = com.example.renderer.NativeDependencyVerifier.verify(directory)
        if (!dependencyCheck.valid) {
            throw IllegalStateException("Android native dependency validation failed: ${dependencyCheck.details}")
        }
    }

    /** Performs the final Java/native GLFW ABI handshake without binding the calling thread. */
    fun validateGlfwHandshake(requireCallbackBridge: Boolean = false, preferLwjgl3: Boolean = true, selectedGlfwName: String? = null): String = if (loaded) {
        runCatching { nativeValidateGlfwHandshake(requireCallbackBridge, preferLwjgl3, selectedGlfwName) }.getOrElse { "FAIL: ${it.message}" }
    } else {
        "FAIL: JNI unavailable"
    }

    @Synchronized
    fun setSurface(surface: Surface?, width: Int, height: Int) {
        if (!loaded) return
        // SurfaceHolder can deliver a replacement/resized Surface while the
        // embedded Minecraft JVM is still rendering. Replacing the native
        // ANativeWindow at that moment destroys EGL state underneath LWJGL
        // threads. Queue the newest surface and apply it only after JLI exits.
        if (isJavaRunning()) {
            deferredSurface = surface
            deferredSurfaceWidth = width
            deferredSurfaceHeight = height
            deferredSurfaceClear = surface == null
            LauncherLogger.warn(
                if (surface == null) {
                    "Android surface clear deferred while embedded Minecraft JVM is running."
                } else {
                    "Android surface replacement deferred while embedded Minecraft JVM is running: ${width}x${height}."
                }
            )
            return
        }
        deferredSurface = null
        deferredSurfaceWidth = 0
        deferredSurfaceHeight = 0
        deferredSurfaceClear = surface == null
        try { nativeSetSurface(surface, width, height) }
        catch (t: Throwable) { LauncherLogger.warn("JNI surface update failed: ${t.message}") }
    }

    @Volatile private var deferredSurfaceClear = false
    @Volatile private var deferredSurface: Surface? = null
    @Volatile private var deferredSurfaceWidth = 0
    @Volatile private var deferredSurfaceHeight = 0

    /**
     * Detaches the Android surface only when the embedded Minecraft JVM is no
     * longer running. Destroying EGL/GLFW state while LWJGL threads are still
     * executing can invalidate native handles underneath the game thread.
     */
    @Synchronized
    fun clearSurface(force: Boolean = false) {
        deferredSurfaceClear = true
        deferredSurface = null
        deferredSurfaceWidth = 0
        deferredSurfaceHeight = 0
        if (isJavaRunning() && !force) {
            LauncherLogger.warn("Android surface cleanup deferred while embedded Minecraft JVM is running.")
            return
        }
        if (loaded) runCatching { nativeGlfwShutdown() }
        if (loaded) runCatching { nativeDestroyEgl() }
        setSurfaceImmediate(null, 0, 0)
    }

    private fun setSurfaceImmediate(surface: Surface?, width: Int, height: Int) {
        if (!loaded) return
        try { nativeSetSurface(surface, width, height) }
        catch (t: Throwable) { LauncherLogger.warn("JNI surface update failed: ${t.message}") }
    }

    /** Applies the newest deferred Surface update once the embedded JVM is gone. */
    @Synchronized
    fun flushDeferredSurfaceClear() {
        if (isJavaRunning()) return
        val pending = deferredSurface
        val pendingWidth = deferredSurfaceWidth
        val pendingHeight = deferredSurfaceHeight
        if (pending != null) {
            deferredSurface = null
            deferredSurfaceWidth = 0
            deferredSurfaceHeight = 0
            deferredSurfaceClear = false
            setSurfaceImmediate(pending, pendingWidth, pendingHeight)
            LauncherLogger.info("Applied deferred Android surface: ${pendingWidth}x${pendingHeight}.")
            return
        }
        if (deferredSurfaceClear) clearSurface(force = true)
    }

    /** Creates an EGL window surface/context backed by the current Android Surface. */
    fun initEgl(): String = if (loaded) runCatching { nativeInitEgl() }.getOrElse { "FAIL: ${it.message}" } else "FAIL: JNI unavailable"
    fun makeEglCurrent(): Boolean = loaded && runCatching { nativeEglMakeCurrent() }.getOrDefault(false)
    fun swapEglBuffers(): Boolean = loaded && runCatching { nativeEglSwapBuffers() }.getOrDefault(false)
    fun eglDisplayHandle(): Long = if (loaded) nativeGetEglDisplay() else 0L
    fun eglContextHandle(): Long = if (loaded) nativeGetEglContext() else 0L
    fun eglSurfaceReadHandle(): Long = if (loaded) nativeGetEglSurfaceRead() else 0L
    fun eglSurfaceDrawHandle(): Long = if (loaded) nativeGetEglSurfaceDraw() else 0L

    /** Performs one real GLES render+swap on the Android GameSurface before Minecraft starts. */
    fun validateEglFrame(): String = if (loaded) {
        runCatching { nativeValidateEglFrame() }.getOrElse { "FAIL: ${it.message}" }
    } else {
        "FAIL: JNI unavailable"
    }

    /** Validates the real GLES capability set that Minecraft/LWJGL will inherit. */
    fun validateOpenGlBootstrap(): String = if (loaded) {
        runCatching { nativeValidateOpenGlBootstrap() }.getOrElse { "FAIL: ${it.message}" }
    } else {
        "FAIL: JNI unavailable"
    }

    /** Atomically prepares the Android EGL/GL rendering state for the embedded Minecraft JVM. */
    fun prepareLaunchGraphics(width: Int, height: Int): String = if (loaded) {
        runCatching { nativePrepareLaunchGraphics(width, height) }.getOrElse { "FAIL: ${it.message}" }
    } else {
        "FAIL: JNI unavailable"
    }

    fun surfaceGeneration(): Long = if (loaded) nativeGetSurfaceGeneration() else 0L

    /** Preflights the actual loaded GLFW binary against the Android Surface. */
    fun prepareGlfw(width: Int, height: Int): Boolean = loaded &&
        runCatching { nativeGlfwPrepare(width, height) }.getOrDefault(false)
    fun makeGlfwCurrent(): Boolean = loaded && runCatching { nativeGlfwMakeCurrent() }.getOrDefault(false)
    fun swapGlfwBuffers(): Boolean = loaded && runCatching { nativeGlfwSwapBuffers() }.getOrDefault(false)
    /** Number of successful Android-surface frame swaps performed through the CraftDroid GLFW bridge. */
    fun renderFrameCount(): Long = if (loaded) runCatching { nativeGetRenderFrameCount() }.getOrDefault(0L) else 0L

    /** Monotonic timestamp (ms) of the most recent successful bridge frame swap, or 0 if none. */
    fun lastRenderFrameTimeMs(): Long = if (loaded) runCatching { nativeGetLastRenderFrameTimeMs() }.getOrDefault(0L) else 0L

    fun shutdownGlfw() { if (loaded) runCatching { nativeGlfwShutdown() } }

    fun surfaceHandle(): Long = if (loaded) nativeGetSurfaceHandle() else 0L
    fun surfaceWidth(): Int = if (loaded) nativeGetSurfaceWidth() else 0
    fun surfaceHeight(): Int = if (loaded) nativeGetSurfaceHeight() else 0

    /** Returns queue depth and delivery/drop/coalescing counters for the Android->Minecraft input bridge. */
    fun inputDiagnostics(): String = if (loaded) {
        runCatching { nativeInputDiagnostics() }.getOrDefault("unavailable")
    } else {
        "unavailable: JNI unavailable"
    }

    fun sendMouse(x: Float, y: Float, dx: Float, dy: Float, button: Int, down: Boolean) {
        if (!loaded) return
        try { nativeMouse(x, y, dx, dy, button, down) } catch (_: Throwable) { }
    }

    fun sendMouseScroll(horizontal: Float, vertical: Float) {
        if (!loaded) return
        try { nativeMouseScroll(horizontal, vertical) } catch (_: Throwable) { }
    }

    fun sendKey(key: Int, down: Boolean, modifiers: Int = 0) {
        if (!loaded) return
        try { nativeKey(key, down, modifiers) } catch (_: Throwable) { }
    }

    fun sendGamepad(axis: Int, value: Float) {
        if (!loaded) return
        try { nativeGamepadAxis(axis, value) } catch (_: Throwable) { }
    }

    fun sendGamepadButton(button: Int, down: Boolean) {
        if (!loaded) return
        try { nativeGamepadButton(button, down) } catch (_: Throwable) { }
    }

    /** Returns [type,key/button,unused,down,a*1000,b*1000,c*1000,d*1000]. */
    fun pollEvent(out: IntArray): Boolean {
        if (!loaded || out.size < 8) return false
        return nativePollEvent(out) != 0
    }

    /** Starts the Android-built JRE in this process through libjli/JLI_Launch.
     * This is required for the GLFW native bridge to share the Android Surface.
     */
    fun launchJava(javaHome: String, arguments: List<String>, environment: Map<String, String>): Int {
        if (!loaded) return -103
        return nativeLaunchJava(javaHome, arguments.toTypedArray(), environment.map { (k, v) -> "$k=$v" }.toTypedArray())
    }

    /** Requests a clean shutdown of the embedded Minecraft JVM. */
    fun requestJavaStop(): Boolean = loaded && runCatching { nativeRequestJavaStop() }.getOrDefault(false)

    /** True while the embedded Minecraft JVM is inside JLI_Launch. */
    fun isJavaRunning(): Boolean = loaded && runCatching { nativeIsJavaRunning() }.getOrDefault(false)

    /** Embedded JVM bridge state: 0=IDLE, 1=STARTING, 2=RUNNING, 3=STOPPING, 4=EXITED (terminal after JLI_Launch returns). */
    fun javaState(): Int = loaded && runCatching { nativeGetJavaState() }.getOrDefault(0)

    fun isLoaded(): Boolean = loaded

    private external fun nativeLoadLibrary(path: String): Boolean
    private external fun nativeValidateNativeStack(directory: String, preferLwjgl3: Boolean, selectedGlfwName: String?): String
    private external fun nativeValidateGlfwHandshake(requireCallbackBridge: Boolean, preferLwjgl3: Boolean, selectedGlfwName: String?): String
    private external fun nativeInitEgl(): String
    private external fun nativeEglMakeCurrent(): Boolean
    private external fun nativeEglSwapBuffers(): Boolean
    private external fun nativeDestroyEgl()
    private external fun nativeGetEglDisplay(): Long
    private external fun nativeGetEglContext(): Long
    private external fun nativeGetEglSurfaceRead(): Long
    private external fun nativeGetEglSurfaceDraw(): Long
    private external fun nativeValidateEglFrame(): String
    private external fun nativeValidateOpenGlBootstrap(): String
    private external fun nativePrepareLaunchGraphics(width: Int, height: Int): String
    private external fun nativeGetSurfaceGeneration(): Long
    private external fun nativeGlfwPrepare(width: Int, height: Int): Boolean
    private external fun nativeGlfwMakeCurrent(): Boolean
    private external fun nativeGlfwSwapBuffers(): Boolean
    private external fun nativeGlfwShutdown()
    private external fun nativeGetRenderFrameCount(): Long
    private external fun nativeGetLastRenderFrameTimeMs(): Long
    private external fun nativeSetSurface(surface: Surface?, width: Int, height: Int)
    private external fun nativeGetSurfaceHandle(): Long
    private external fun nativeGetSurfaceWidth(): Int
    private external fun nativeGetSurfaceHeight(): Int
    private external fun nativeInputDiagnostics(): String
    private external fun nativeMouse(x: Float, y: Float, dx: Float, dy: Float, button: Int, down: Boolean)
    private external fun nativeMouseScroll(horizontal: Float, vertical: Float)
    private external fun nativeKey(key: Int, down: Boolean, modifiers: Int)
    private external fun nativeGamepadAxis(axis: Int, value: Float)
    private external fun nativeGamepadButton(button: Int, down: Boolean)
    private external fun nativePollEvent(out: IntArray): Int
    private external fun nativeLaunchJava(javaHome: String, arguments: Array<String>, environment: Array<String>): Int
    private external fun nativeRequestJavaStop(): Boolean
    private external fun nativeIsJavaRunning(): Boolean
    private external fun nativeGetJavaState(): Int
}
