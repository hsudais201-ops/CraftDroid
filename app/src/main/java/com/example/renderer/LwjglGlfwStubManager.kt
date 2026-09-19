package com.example.renderer

import android.content.Context
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.zip.ZipFile

/**
 * Installs the Android GLFW Java stub used by Pojav-style Minecraft launchers.
 * The stub replaces desktop LWJGL GLFW classes with Android-compatible Java
 * implementations and is loaded before the version's normal LWJGL jars.
 */
class LwjglGlfwStubManager(
    private val context: Context,
    private val fileSystem: MinecraftFileSystem,
    private val client: OkHttpClient
) {
    companion object {
        // The standalone lwjgl3-glfw-java repository is archived. Prefer the
        // GLFW stub shipped by the PojavLauncher source tree, which is the
        // maintained compatibility target for their launcher build.
        private const val STUB_URL =
            "https://raw.githubusercontent.com/TeamPojavLauncher/PojavLauncher/master/app_pojavlauncher/src/main/assets/components/lwjgl3/lwjgl-glfw-classes.jar"
        private const val FALLBACK_URL =
            "https://raw.githubusercontent.com/PojavLauncherTeam/PojavLauncher/v3_openjdk/app_pojavlauncher/src/main/assets/components/lwjgl3/lwjgl-glfw-classes.jar"
        private const val ARCHIVED_FALLBACK_URL =
            "https://raw.githubusercontent.com/PojavLauncherTeam/lwjgl3-glfw-java/master/target/lwjgl-glfw-classes.jar"
        private const val STUB_FILE = "lwjgl-glfw-classes.jar"
    }

    private val target: File
        get() = File(fileSystem.rootDir, "lwjgl3/$STUB_FILE")

    fun ensureInstalled(): File {
        target.parentFile?.mkdirs()
        if (isValidJar(target)) {
            installCallbackPatch()
            return target
        }

        var last: Throwable? = null
        for (url in listOf(STUB_URL, FALLBACK_URL, ARCHIVED_FALLBACK_URL)) {
            try {
                LauncherLogger.info("Downloading Android GLFW Java stub from $url")
                download(url, target)
                val validation = validateStubJar(target)
                if (!validation.isValid) error("Downloaded GLFW stub is incompatible: ${validation.reason}")
                LauncherLogger.info("Android GLFW Java stub installed: ${target.absolutePath} (${target.length()} bytes)")
                installCallbackPatch()
                return target
            } catch (t: Throwable) {
                last = t
                target.delete()
                LauncherLogger.warn("GLFW stub download failed: ${t.message}")
            }
        }
        throw IllegalStateException("Unable to install Android GLFW Java stub: ${last?.message}")
    }

    fun callbackPatchFile(): File {
        val out = File(target.parentFile, "craftdroid-callback-bridge.jar")
        installCallbackPatch(out)
        return out
    }

    private fun installCallbackPatch(destination: File = File(target.parentFile, "craftdroid-callback-bridge.jar")) {
        if (destination.isFile && destination.length() > 100) return
        context.assets.open("craftdroid-callback-bridge.jar").use { input ->
            destination.outputStream().use { output -> input.copyTo(output) }
        }
    }

    private data class StubValidation(val isValid: Boolean, val reason: String)

    private fun validateStubJar(file: File): StubValidation {
        if (!file.isFile || file.length() < 10_000) {
            return StubValidation(false, "file is missing or suspiciously small")
        }
        return runCatching {
            ZipFile(file).use { zip ->
                val glfw = zip.getEntry("org/lwjgl/glfw/GLFW.class")
                    ?: return StubValidation(false, "missing org/lwjgl/glfw/GLFW.class")
                val callback = zip.getEntry("org/lwjgl/glfw/CallbackBridge.class")
                    ?: return StubValidation(false, "missing org/lwjgl/glfw/CallbackBridge.class")

                // The Android bridge relies on CallbackBridge's callback entry
                // points. We validate bytecode symbols without loading the class
                // into the launcher JVM, avoiding class-loader pollution.
                val callbackBytes = zip.getInputStream(callback).use { it.readBytes() }
                val requiredSymbols = listOf(
                    "receiveCallback",
                    "nativeSendData",
                    "nativeSetInputReady",
                    "nativeClipboard",
                    "nativeSetGrabbing"
                )
                val missing = requiredSymbols.filter { symbol ->
                    callbackBytes.indexOf(symbol.toByteArray()) < 0
                }
                if (missing.isNotEmpty()) {
                    return StubValidation(false, "CallbackBridge is missing: ${missing.joinToString()}")
                }

                val glfwBytes = zip.getInputStream(glfw).use { it.readBytes() }
                if (glfwBytes.indexOf("glfwInit".toByteArray()) < 0 ||
                    glfwBytes.indexOf("glfwPollEvents".toByteArray()) < 0) {
                    return StubValidation(false, "GLFW class does not expose the expected Android stub API")
                }
                StubValidation(true, "compatible GLFW/CallbackBridge classes")
            }
        }.getOrElse { StubValidation(false, it.message ?: "invalid ZIP/JAR") }
    }

    private fun isValidJar(file: File): Boolean = validateStubJar(file).isValid

    private fun download(url: String, destination: File) {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "CraftDroid-Launcher/1.7")
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("HTTP ${response.code} for $url")
            val body = response.body ?: error("Empty response from $url")
            FileOutputStream(destination).use { out -> body.byteStream().use { it.copyTo(out) } }
        }
    }
}
