package com.example.renderer

import android.content.Context
import android.os.Build
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/**
 * Installs the Android-native bridge used by Java Minecraft launchers.
 *
 * CraftDroid deliberately downloads these open-source components from their
 * upstream release pages instead of redistributing someone else's APK inside
 * CraftDroid. This keeps the launcher small and makes upstream updates possible.
 */
class NativeComponentManager(
    private val context: Context,
    private val fileSystem: MinecraftFileSystem,
    private val client: OkHttpClient
) {
    data class NativeStack(
        val directory: File,
        val abi: String,
        val libraries: List<String>
    ) {
        val hasGlfw: Boolean get() = libraries.any { it.equals("libglfw.so", true) || it.contains("glfw", true) }
        val hasPojavExec: Boolean get() = libraries.any { it.contains("pojavexec", true) }
        val hasLwjgl: Boolean get() = libraries.any {
            it.equals("liblwjgl.so", true) ||
                it.equals("liblwjgl3.so", true) ||
                it.contains("lwjgl", true)
        }
        val hasGl4es: Boolean get() = libraries.any { it.contains("gl4es", true) }
        val hasMobileGlues: Boolean get() = libraries.any { it.contains("mobileglues", true) }
        val hasOpenAl: Boolean get() = libraries.any { it.contains("openal", true) }
        val hasZink: Boolean get() = libraries.any { it.contains("zink", true) || it.contains("mesa", true) }
    }

    companion object {
        // Pin the known current TeamPojavLauncher native architecture.
        // Pin the known current upstream release instead of following `latest`.
        // `latest` can change its native ABI/backend without a CraftDroid update.
        private const val POJAV_APK_URL =
            "https://github.com/TeamPojavLauncher/PojavLauncher/releases/download/pojav-legacy/Pojavlauncher-release.apk"
        private const val POJAV_APK_SHA256 =
            "4772352ad7d97784fb4ccdd951759d22788e6e61fd82e61b85eeab16f69d320f"
        private const val MOBILEGLUES_APK =
            "https://github.com/MobileGL-Dev/MobileGlues-release/releases/download/V2.0.0/MobileGlues_2.0.0.apk"
        private const val MOBILEGLUES_SHA256 =
            "a7e1eb29731fdece7ab3af7fb00692b856f1808a7544436e7b3eb6c08355581a"
    }

    private val stackRoot: File
        get() = File(fileSystem.rendererDir, "android-native-stack")

    fun archName(): String {
        val abi = Build.SUPPORTED_ABIS.firstOrNull()?.lowercase().orEmpty()
        return when {
            abi == "arm64-v8a" || abi.contains("aarch64") -> "arm64-v8a"
            abi == "armeabi-v7a" || abi.contains("armeabi") -> "armeabi-v7a"
            abi == "x86_64" -> "x86_64"
            abi == "x86" -> "x86"
            else -> error("Unsupported Android ABI: $abi")
        }
    }

    suspend fun ensureInstalled(onStatus: (String) -> Unit, requiredLwjglVersion: String? = null): NativeStack = withContext(Dispatchers.IO) {
        val abi = archName()
        val packageKey = requiredLwjglVersion?.replace(Regex("[^A-Za-z0-9._-]"), "_") ?: "auto"
        val target = File(stackRoot, "lwjgl/$packageKey/$abi").apply { mkdirs() }
        LauncherLogger.info("Preparing versioned Android LWJGL package: version=${requiredLwjglVersion ?: "auto"}, ABI=$abi, path=${target.absolutePath}")
        installCraftDroidBridge(target)
        var stack = inspect(target, abi)
        val installedAbiCheck = NativeAbiVerifier.verify(target, abi)
        if (!installedAbiCheck.valid) {
            LauncherLogger.warn("Installed native stack ABI check failed; reinstalling: ${installedAbiCheck.details}")
        }
        if (isUsable(stack) && installedAbiCheck.valid && (requiredLwjglVersion == null || nativeMatches(requiredLwjglVersion, target))) {
            return@withContext stack
        }

        onStatus("Downloading Android native bridge…")
        val pojavApk = File(stackRoot, "pojav-native.apk")
        var downloaded = false
        var lastError: Throwable? = null
        try {
            download(POJAV_APK_URL, pojavApk)
            if (!sha256(pojavApk).equals(POJAV_APK_SHA256, true)) {
                pojavApk.delete()
                throw SecurityException("Pojav native bridge checksum verification failed")
            }
            downloaded = true
        } catch (e: Throwable) {
            lastError = e
            LauncherLogger.warn("Native bridge download failed: " + e.message)
        }
        if (!downloaded) {
            throw IllegalStateException("Could not download the verified Pojav native bridge: " + lastError?.message)
        }

        onStatus("Extracting GLFW/OpenGL/audio native libraries…")
        extractAbiLibraries(pojavApk, abi, target)
        stack = inspect(target, abi)
        val downloadedAbiCheck = NativeAbiVerifier.verify(target, abi)
        if (!downloadedAbiCheck.valid) {
            throw IllegalStateException("Downloaded Android native stack has an ABI mismatch: ${downloadedAbiCheck.details}")
        }

        // Do not force-install MobileGlues when the selected upstream package
        // already contains a usable GL4ES/Zink backend. This keeps first launch
        // smaller and avoids turning an optional renderer into a hard dependency.
        // MobileGlues is fetched only when no graphics backend is available.
        if (!stack.hasGl4es && !stack.hasZink && !stack.hasMobileGlues) {
            onStatus("Installing MobileGlues renderer…")
            val mgApk = File(stackRoot, "mobileglues.apk")
            if (!mgApk.isFile || !sha256(mgApk).equals(MOBILEGLUES_SHA256, true)) {
                download(MOBILEGLUES_APK, mgApk)
                if (!sha256(mgApk).equals(MOBILEGLUES_SHA256, true)) {
                    mgApk.delete()
                    throw SecurityException("MobileGlues checksum verification failed")
                }
            }
            extractAbiLibraries(mgApk, abi, target)
        }

        stack = inspect(target, abi)
        val finalAbiCheck = NativeAbiVerifier.verify(target, abi)
        if (!finalAbiCheck.valid) {
            throw IllegalStateException("Android native stack ABI validation failed: ${finalAbiCheck.details}")
        }
        val dependencyCheck = NativeDependencyVerifier.verify(target)
        if (!dependencyCheck.valid) {
            throw IllegalStateException("Android native stack dependency validation failed: ${dependencyCheck.details}")
        }
        if (!isUsable(stack)) {
            throw IllegalStateException(
                "Native bridge incomplete for $abi. Found: ${stack.libraries.sorted().joinToString()}. " +
                    "Required GLFW/PojavExec/OpenGL libraries were not found."
            )
        }
        if (requiredLwjglVersion != null && !nativeMatches(requiredLwjglVersion, target)) {
            val detected = detectLwjglVersion(target) ?: "unknown"
            throw IllegalStateException(
                "No Android LWJGL native package matching $requiredLwjglVersion is available for $abi " +
                    "(detected $detected). CraftDroid will not substitute an incompatible native binary."
            )
        }

        onStatus("Android native graphics/audio bridge ready")
        LauncherLogger.info("Native stack ready: ABI=$abi libs=${stack.libraries.size}; requestedLWJGL=${requiredLwjglVersion ?: "auto"}")
        stack
    }

    fun inspectInstalled(): NativeStack? {
        val abi = runCatching { archName() }.onFailure { LauncherLogger.warn("Native stack ABI probe failed: " + it.message) }.getOrNull() ?: return null
        // Runtime stacks are stored under lwjgl/<version-or-auto>/<abi>.
        // The old diagnostic path used <root>/<abi>, which made a correctly
        // installed stack appear to be missing. Prefer the active launch
        // profile and fall back to any matching ABI directory.
        val candidates = stackRoot.listFiles()?.asSequence()
            ?.filter { it.isDirectory }
            ?.map { File(it, abi) }
            ?.filter { it.isDirectory }
            ?.toList()
            .orEmpty()
        val stackDir = candidates.firstOrNull { isUsable(inspect(it, abi)) }
            ?: candidates.firstOrNull { inspect(it, abi).libraries.isNotEmpty() }
            ?: File(stackRoot, "lwjgl/auto/$abi")
        val stack = inspect(stackDir, abi)
        return stack.takeIf { it.libraries.isNotEmpty() }
    }

    private fun installCraftDroidBridge(destination: File) {
        val source = File(context.applicationInfo.nativeLibraryDir, "libcraftdroidbridge.so")
        val target = File(destination, source.name)
        if (!source.isFile) return
        if (!target.isFile || target.length() != source.length()) {
            source.inputStream().use { input -> target.outputStream().use { output -> input.copyTo(output) } }
            target.setExecutable(true, false)
        }
    }

    private fun isUsable(stack: NativeStack): Boolean {
        // The current Pojav rewrite changed its native layout and no longer
        // guarantees a library literally named `pojavexec` in every release.
        // Treat GLFW + LWJGL + a graphics backend as the hard requirement.
        // AWT/execution/audio helpers are validated separately when the selected
        // Minecraft version actually needs them.
        return stack.hasGlfw &&
            stack.hasLwjgl &&
            (stack.hasGl4es || stack.hasMobileGlues || stack.hasZink)
    }

    private fun inspect(dir: File, abi: String): NativeStack {
        val libs = dir.listFiles()?.filter { it.isFile && it.name.endsWith(".so") }
            ?.map { it.name }
            .orEmpty()
        return NativeStack(dir, abi, libs)
    }

    private fun nativeMatches(requiredVersion: String, dir: File): Boolean {
        val detected = detectLwjglVersion(dir) ?: return false
        return if (requiredVersion.startsWith("2.")) {
            // Legacy Minecraft uses the LWJGL2 compatibility layer, while the
            // Android native implementation remains LWJGL3. Any compatible 3.x
            // native build is preferable to falsely requiring one hard-coded
            // patch release.
            detected.startsWith("3.")
        } else {
            // Upstream Pojav now installs the appropriate LWJGL Java version per
            // game version. Its Android native bridge is not a one-to-one Maven
            // artifact, so require the same major/minor family rather than an
            // exact patch string. Exact native compatibility is additionally
            // checked through the actual JNI handshake before JLI_Launch.
            val required = requiredVersion.split('.')
            val detectedParts = detected.split('.')
            required.size >= 2 && detectedParts.size >= 2 &&
                required[0] == detectedParts[0] && required[1] == detectedParts[1]
        }
    }

    private fun detectLwjglVersion(dir: File): String? {
        val candidates = dir.listFiles()?.filter {
            it.isFile && it.name.startsWith("liblwjgl") && it.name.endsWith(".so")
        }.orEmpty()
        for (file in candidates) {
            val version = runCatching {
                val bytes = file.inputStream().use { input ->
                    val buffer = ByteArray(2 * 1024 * 1024)
                    val n = input.read(buffer)
                    buffer.copyOf(if (n > 0) n else 0)
                }
                val text = buildString(bytes.size) {
                    for (b in bytes) {
                        val c = b.toInt() and 0xff
                        append(if (c in 32..126) c.toChar() else ' ')
                    }
                }
                Regex("(?:LWJGL|lwjgl)[^0-9]{0,40}(3\\.[0-9]+\\.[0-9]+)").find(text)?.groupValues?.getOrNull(1)
                    ?: Regex("\\b(3\\.[0-9]+\\.[0-9]+)\\b").find(text)?.groupValues?.getOrNull(1)
            }.getOrNull()
            if (version != null) return version
        }
        return null
    }

    private fun download(url: String, destination: File) {
        val request = Request.Builder()
            .url(url)
            .header("User-Agent", "CraftDroid-Launcher/1.4")
            .build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) error("HTTP ${response.code} for $url")
            val body = response.body ?: error("Empty response from $url")
            destination.parentFile?.mkdirs()
            FileOutputStream(destination).use { out -> body.byteStream().use { it.copyTo(out) } }
        }
    }

    private fun extractAbiLibraries(apk: File, abi: String, destination: File) {
        ZipInputStream(FileInputStream(apk).buffered()).use { zip ->
            while (true) {
                val entry = zip.nextEntry ?: break
                val prefix = "lib/$abi/"
                if (!entry.isDirectory && entry.name.startsWith(prefix) && entry.name.endsWith(".so")) {
                    val fileName = File(entry.name).name
                    val output = File(destination, fileName)
                    FileOutputStream(output).use { zip.copyTo(it) }
                    output.setExecutable(true, false)
                }
                zip.closeEntry()
            }
        }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(128 * 1024)
            while (true) {
                val n = input.read(buffer)
                if (n <= 0) break
                digest.update(buffer, 0, n)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
