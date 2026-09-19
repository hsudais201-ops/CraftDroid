package com.example.runtime

import android.os.Build
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.apache.commons.compress.archivers.tar.TarArchiveInputStream
import org.tukaani.xz.XZInputStream
import java.io.BufferedInputStream
import java.io.BufferedReader
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.InputStreamReader
import java.nio.file.Files
import java.net.URI
import java.security.MessageDigest
import java.util.zip.ZipInputStream

/** A real Android/OpenJDK runtime installed under app-private executable storage. */
data class JavaRuntime(
    val majorVersion: Int,
    val name: String,
    val javaHome: File,
    val javaExecutable: File,
    val isInstalled: Boolean,
    val isValid: Boolean,
    val versionDetails: String = ""
)

class JavaRuntimeManager(
    private val fileSystem: MinecraftFileSystem,
    private val okHttpClient: OkHttpClient
) {
    private val _runtimes = MutableStateFlow<List<JavaRuntime>>(emptyList())
    val runtimes: StateFlow<List<JavaRuntime>> = _runtimes.asStateFlow()

    private val _isTesting = MutableStateFlow(false)
    val isTesting: StateFlow<Boolean> = _isTesting.asStateFlow()

    companion object {
        private const val RUNTIME_CATALOG_VERSION = 2
        private val SUPPORTED_MAJORS = listOf(8, 17, 21, 25)

        // Public, versioned JRE mirrors used by Amethyst's Android runtime builds.
        // Java 17/21 use the current published release assets; Java 8 uses its
        // dedicated download_jre8 release because that release is the stable
        // download center for the four Java 8 Android architectures.
        // AngelAuraMC publishes the Android JREs as versioned GitHub release
        // assets. This is the same JRE distribution family used by the current
        // Amethyst Android launcher. Keep the tag pinned instead of following
        // /latest so a launcher update cannot silently replace the runtime ABI.
        private const val JRE_BASE =
            "https://github.com/AngelAuraMC/angelauramc-openjdk-build/releases/download/"

        private val JRE_TAGS = mapOf(
            8 to "download_jre8",
            17 to "release",
            21 to "release",
            25 to "release"
        )

        private val JRE_SHA256 = mapOf(
            "17/arm" to "4a9134f1ebf6340dd855805d351712462cddab6f3c2684da7e7da10ccf06648d",
            "17/arm64" to "e162c860fe05ee4a4e4af7606437419879f6c748386a7b09fa77d10db6a64091",
            "17/x86" to "223a2d54606a9eb853c8451cf1d6bda1a8f09cb357f40b790140e57d45731ed7",
            "17/x86_64" to "893e27d2aed8b40407f29fe939e2a0f193e5d55f72892a303db634b0808a2b61",
            "21/arm" to "96c297487def64666e379a9a363d9955c05b1a0b091b0cf24af88359a66f394a",
            "21/arm64" to "8d41ec401ee59f7722df60ed991f81ad146e130452804bfdd8a05d3436f7bbfe",
            "21/x86" to "9b8c7d10c5f751acb3b33506593da44ece52a0fd03e0b3c283ba08a7f285a40f",
            "21/x86_64" to "cb88723961f5f9ad63afa1f212eb199816c27cabfd7dc66567bde1d8fb69713b",
            "25/arm" to "9ae13aee9cba7b2d2d8f40965061667e876d7380d866f37a992db3eff296ffb5",
            "25/arm64" to "d3eb7afe2240c26728a1bb440502c5f18ac3883e932d202dd7f0c9bcbbce4c37",
            "8/arm" to "9dbee3b09af5f170e2ed9dd596bc81d0e573c88f8bf760c59c8fadbb9073d1e7",
            "8/arm64" to "9a59124d9791957d55c68be664ab76831f336cf2e1e1cd4414220c6fdbf0e06d",
            "8/x86" to "b96ce49fab52b28688dccc1a7d85dfc6d0f4048636aac826e1967524b28f75af",
            "8/x86_64" to "b1fbcef4965c17925894febe8216d089c6dd47b37950b5f945a89616443c1d0e"
        )
    }

    init { refreshRuntimes() }

    fun getArch(): String {
        val abi = Build.SUPPORTED_ABIS.firstOrNull()?.lowercase() ?: return "arm64"
        return when {
            abi.contains("arm64") || abi.contains("aarch64") -> "arm64"
            abi.contains("x86_64") || abi.contains("amd64") -> "x86_64"
            abi.contains("armeabi") || abi.contains("armv7") -> "arm"
            abi.contains("x86") -> "x86"
            else -> "arm64"
        }
    }

    fun refreshRuntimes(): List<JavaRuntime> {
        val list = SUPPORTED_MAJORS.map { major ->
            val runtimeHome = File(fileSystem.javaDir, "java-$major")
            val javaExe = File(runtimeHome, "bin/java")
            val installed = javaExe.isFile
            val validation = if (installed) testJavaExecutable(javaExe) else false to "Not installed"
            if (installed) runCatching { javaExe.setExecutable(true, false) }
            JavaRuntime(
                majorVersion = major,
                name = "Java $major OpenJDK (${validation.second})",
                javaHome = runtimeHome,
                javaExecutable = javaExe,
                isInstalled = installed,
                isValid = installed && validation.first,
                versionDetails = validation.second
            )
        }
        _runtimes.value = list
        return list
    }

    /**
     * Select only a runtime that is known-compatible with the requested Java
     * level. Never silently jump from Java 17 to 21/25 (or 8 to 17): newer
     * JVMs can change verifier, module, GC, or native behaviour and can make
     * an otherwise valid Minecraft installation fail at startup.
     *
     * Minecraft 1.17-era manifests can request Java 16. CraftDroid uses its
     * Android Java 17 runtime for that case because the launcher does not ship
     * a separate Java 16 mobile image. Java 17 is a forward-compatible
     * execution target for the Java-16 bytecode used by that release family.
     */
    fun getBestRuntime(requiredMajor: Int): JavaRuntime? {
        val compatibleMajors = when (requiredMajor) {
            16 -> listOf(17)
            8, 17, 21, 25 -> listOf(requiredMajor)
            else -> emptyList()
        }
        if (compatibleMajors.isEmpty()) return null
        return refreshRuntimes().firstOrNull {
            it.majorVersion in compatibleMajors && it.isValid
        }
    }

    suspend fun ensureRuntime(majorVersion: Int, onStatus: (String) -> Unit): JavaRuntime = withContext(Dispatchers.IO) {
        val supportedRequest = majorVersion in SUPPORTED_MAJORS || majorVersion == 16
        require(supportedRequest) { "Minecraft requires unsupported Java $majorVersion" }
        getBestRuntime(majorVersion)?.let { return@withContext it }
        val installMajor = if (majorVersion == 16) 17 else majorVersion
        if (majorVersion == 16) {
            onStatus("Minecraft requests Java 16; installing/using the compatible Android Java 17 runtime")
        }
        if (!installRuntime(installMajor, onStatus)) {
            throw IllegalStateException(
                "Java $majorVersion is not installed. Compatible OpenJDK $installMajor could not be installed automatically on this device."
            )
        }
        getBestRuntime(majorVersion)
            ?: throw IllegalStateException("Downloaded Java $installMajor failed runtime validation for requested Java $majorVersion.")
    }

    suspend fun testJava(majorVersion: Int): Pair<Boolean, String> = withContext(Dispatchers.IO) {
        _isTesting.value = true
        try {
            val runtime = _runtimes.value.firstOrNull { it.majorVersion == majorVersion }
                ?: return@withContext false to "Java $majorVersion is not registered"
            if (!runtime.isInstalled) return@withContext false to "Java $majorVersion is not installed"
            testJavaExecutable(runtime.javaExecutable).also { refreshRuntimes() }
        } finally { _isTesting.value = false }
    }

    private fun testJavaExecutable(executable: File): Pair<Boolean, String> {
        if (!executable.isFile) return false to "java binary missing"
        val javaHome = executable.parentFile?.parentFile
            ?: return false to "invalid Java home"

        // Android JRE packages may use either a desktop-style layout or a
        // Pojav-style ABI-specific layout. Validate the actual files instead
        // of assuming lib/jli and lib/server always exist at fixed paths.
        val jli = listOf(
            File(javaHome, "lib/jli/libjli.so"),
            File(javaHome, "lib/aarch64/jli/libjli.so"),
            File(javaHome, "lib/arm/jli/libjli.so"),
            File(javaHome, "lib/x86_64/jli/libjli.so"),
            File(javaHome, "lib/i386/jli/libjli.so")
        ).firstOrNull { it.isFile }
            ?: return false to "Android JRE missing libjli.so (standard/multi-arch layouts checked)"

        val vm = listOf(
            File(javaHome, "lib/server/libjvm.so"),
            File(javaHome, "lib/client/libjvm.so"),
            File(javaHome, "lib/libjvm.so"),
            File(javaHome, "lib/aarch64/libjvm.so"),
            File(javaHome, "lib/arm/libjvm.so"),
            File(javaHome, "lib/x86_64/libjvm.so"),
            File(javaHome, "lib/i386/libjvm.so")
        ).firstOrNull { it.isFile }
            ?: return false to "Android JRE missing libjvm.so"

        return try {
            executable.setExecutable(true, false)
            val processBuilder = ProcessBuilder(executable.absolutePath, "-version")
                .redirectErrorStream(true)
            val processEnvironment = processBuilder.environment()
            val runtimeLibDirs = listOfNotNull(
                jli.parentFile,
                jli.parentFile?.parentFile,
                vm.parentFile,
                vm.parentFile?.parentFile
            ).filter { it.isDirectory }.map { it.absolutePath }.distinct()
            val existingLd = processEnvironment["LD_LIBRARY_PATH"].orEmpty()
            processEnvironment["LD_LIBRARY_PATH"] =
                (runtimeLibDirs + existingLd.split(File.pathSeparator).filter { it.isNotBlank() })
                    .distinct().joinToString(File.pathSeparator)
            processEnvironment["JAVA_HOME"] = javaHome.absolutePath
            processEnvironment["JLI_HOME"] = jli.parentFile?.absolutePath.orEmpty()

            val process = processBuilder.start()
            val output = buildString {
                BufferedReader(InputStreamReader(process.inputStream)).useLines { lines ->
                    lines.take(12).forEach { appendLine(it) }
                }
            }
            val exit = process.waitFor()
            if (exit == 0 && output.contains("version", ignoreCase = true)) {
                val firstLine = output.lineSequence().firstOrNull { it.isNotBlank() }?.trim().orEmpty()
                val detectedMajor = parseJavaMajor(output)
                if (detectedMajor == null) {
                    false to "Unable to determine Java major version: ${output.take(220).trim()}"
                } else {
                    true to "Java $detectedMajor: $firstLine"
                }
            } else false to "Java exited with $exit: ${output.take(220).trim()}"
        } catch (e: Exception) {
            false to "Execution failed: ${e.message ?: e.javaClass.simpleName}"
        }
    }

    private fun parseJavaMajor(output: String): Int? {
        val match = Regex("(?:version\\s+\"|openjdk\\s+)(\\d+)(?:[.\\s\"_-]|$)", RegexOption.IGNORE_CASE)
            .find(output)
            ?: Regex("\\b(?:java|openjdk)\\s+(\\d+)", RegexOption.IGNORE_CASE).find(output)
        val raw = match?.groupValues?.getOrNull(1) ?: return null
        return raw.toIntOrNull()
    }

    private data class RuntimePackage(
        val major: Int,
        val arch: String,
        val url: String,
        val sha256: String?
    )

    private fun packageFor(major: Int, arch: String): RuntimePackage? {
        // Java 8 is a real Android JRE published for all four supported ABIs.
        // Its dedicated release exposes machine-readable SHA-256 digests.
        if (major !in SUPPORTED_MAJORS) return null
        val fileName = "jre$major-android-$arch.tar.xz"
        val tag = JRE_TAGS[major] ?: return null
        val sha = JRE_SHA256["$major/$arch"]?.takeIf { it.length == 64 } ?: return null
        return RuntimePackage(
            major = major,
            arch = arch,
            url = JRE_BASE + tag + "/" + fileName,
            sha256 = sha
        )
    }

    private fun download(url: String, destination: File) {
        require(URI(url).scheme?.equals("https", true) == true) {
            "Non-HTTPS runtime URL rejected: $url"
        }
        destination.parentFile?.mkdirs()
        for (attempt in 0 until 3) {
            val resumeBytes = if (destination.isFile) destination.length() else 0L
            val builder = Request.Builder().url(url)
                .header("User-Agent", "CraftDroid-Launcher/1.4")
            if (resumeBytes > 0L) builder.header("Range", "bytes=" + resumeBytes + "-")
            val response = okHttpClient.newCall(builder.build()).execute()
            var retry = false
            response.use {
                if (it.code == 416 && resumeBytes > 0L) {
                    destination.delete()
                    retry = true
                } else {
                    if (!it.isSuccessful) error("HTTP " + it.code)
                    val body = it.body ?: error("Empty runtime download")
                    val append = resumeBytes > 0L && it.code == 206
                    FileOutputStream(destination, append).use { out ->
                        body.byteStream().use { input -> input.copyTo(out) }
                        out.fd.sync()
                    }
                    return
                }
            }
            if (!retry || attempt >= 2) error("HTTP 416 after runtime download resume reset")
        }
        error("Runtime download exhausted retry attempts")
    }
    private fun verifySha256(file: File, expected: String): Boolean {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(1024 * 128)
            while (true) {
                val read = input.read(buffer)
                if (read <= 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }.equals(expected, true)
    }

    private fun safeOutput(baseDir: File, name: String): File {
        val clean = name.replace('\\', '/')
        if (clean.startsWith("/") || clean.split('/').any { it == ".." }) {
            throw SecurityException("Blocked unsafe archive entry: $name")
        }
        val output = File(baseDir, clean).canonicalFile
        val base = baseDir.canonicalFile
        if (output.path != base.path && !output.path.startsWith(base.path + File.separator)) {
            throw SecurityException("Blocked archive path traversal: $name")
        }
        return output
    }

    private fun extractZip(archive: File, destination: File) {
        destination.mkdirs()
        ZipInputStream(BufferedInputStream(FileInputStream(archive))).use { zis ->
            while (true) {
                val entry = zis.nextEntry ?: break
                if (entry.isDirectory) continue
                val out = safeOutput(destination, entry.name)
                out.parentFile?.mkdirs()
                FileOutputStream(out).use { zis.copyTo(it) }
                zis.closeEntry()
            }
        }
    }

    private fun extractTarXz(archive: File, destination: File) {
        destination.mkdirs()
        TarArchiveInputStream(XZInputStream(BufferedInputStream(FileInputStream(archive)))).use { tis ->
            while (true) {
                val entry = tis.nextTarEntry ?: break
                val out = safeOutput(destination, entry.name)
                when {
                    entry.isDirectory -> out.mkdirs()
                    entry.isSymbolicLink -> {
                        val target = entry.linkName.replace('\\', '/')
                        val targetFile = File(out.parentFile, target).canonicalFile
                        val base = destination.canonicalFile
                        if (targetFile.path != base.path && !targetFile.path.startsWith(base.path + File.separator)) {
                            throw SecurityException("Blocked unsafe runtime symlink: ${entry.name} -> $target")
                        }
                        out.parentFile?.mkdirs()
                        runCatching { Files.deleteIfExists(out.toPath()) }
                        android.system.Os.symlink(targetFile.path, out.path)
                    }
                    entry.isFile -> {
                        out.parentFile?.mkdirs()
                        FileOutputStream(out).use { tis.copyTo(it) }
                        if (out.parentFile?.name == "bin" || out.name == "jspawnhelper") out.setExecutable(true, false)
                    }
                }
            }
        }
    }

    private fun findJavaHome(root: File): File? {
        if (File(root, "bin/java").isFile) return root
        val children = root.listFiles()?.sortedBy { it.name } ?: return null
        for (child in children.take(32)) {
            if (!child.isDirectory) continue
            val found = findJavaHomeLimited(child, 4)
            if (found != null) return found
        }
        return null
    }

    private fun findJavaHomeLimited(root: File, depth: Int): File? {
        if (File(root, "bin/java").isFile) return root
        if (depth <= 0) return null
        root.listFiles()?.forEach { child ->
            if (child.isDirectory) findJavaHomeLimited(child, depth - 1)?.let { return it }
        }
        return null
    }

    suspend fun installRuntime(majorVersion: Int, onStatus: (String) -> Unit): Boolean = withContext(Dispatchers.IO) {
        try {
            val arch = getArch()
            val pkg = packageFor(majorVersion, arch)
                ?: throw IllegalStateException("No verified Android OpenJDK " + majorVersion + " package is published for ABI " + arch + ". The launcher refuses to install an unverified or desktop-only runtime.")

            val downloadDir = File(fileSystem.runtimeDir, "downloads")
            val archive = File(downloadDir, "jre-$majorVersion-${pkg.arch}.tar.xz")
            LauncherLogger.info("Java runtime source: ${pkg.url}")
            val staging = File(fileSystem.javaDir, "java-$majorVersion.staging")
            val target = File(fileSystem.javaDir, "java-$majorVersion")

            onStatus("Downloading Android OpenJDK $majorVersion (${pkg.arch})…")
            if (!archive.exists() || (pkg.sha256 != null && !verifySha256(archive, pkg.sha256))) {
                archive.delete()
                download(pkg.url, archive)
            }
            if (pkg.sha256 != null && !verifySha256(archive, pkg.sha256)) {
                archive.delete()
                throw SecurityException("OpenJDK $majorVersion SHA-256 verification failed")
            }

            onStatus("Extracting OpenJDK $majorVersion…")
            staging.deleteRecursively()
            extractTarXz(archive, staging)
            val stagedJavaHome = findJavaHome(staging)
                ?: throw IllegalStateException("Downloaded archive does not contain bin/java")

            val stagedJava = File(stagedJavaHome, "bin/java")
            stagedJava.setExecutable(true, false)
            val stagedValidation = testJavaExecutable(stagedJava)
            if (!stagedValidation.first) {
                staging.deleteRecursively()
                throw IllegalStateException("Extracted Java failed validation: ${stagedValidation.second}")
            }

            target.parentFile?.mkdirs()
            val backup = File(fileSystem.javaDir, "java-$majorVersion.backup-${System.currentTimeMillis()}")
            if (target.exists() && !target.renameTo(backup)) {
                staging.deleteRecursively()
                throw IllegalStateException("Could not safely replace existing Java $majorVersion runtime")
            }

            try {
                if (!stagedJavaHome.renameTo(target)) {
                    stagedJavaHome.copyRecursively(target, overwrite = true)
                }
                val javaExe = File(target, "bin/java")
                javaExe.setExecutable(true, false)
                val validation = testJavaExecutable(javaExe)
                if (!validation.first) {
                    target.deleteRecursively()
                    if (backup.exists()) backup.renameTo(target)
                    throw IllegalStateException("Installed Java failed validation: ${validation.second}")
                }
                backup.deleteRecursively()
            } catch (e: Exception) {
                if (backup.exists() && !target.exists()) backup.renameTo(target)
                staging.deleteRecursively()
                throw e
            } finally {
                staging.deleteRecursively()
            }

            refreshRuntimes()
            LauncherLogger.info("Installed Android OpenJDK $majorVersion/${pkg.arch}: ${validation.second}")
            onStatus("OpenJDK $majorVersion ready")
            true
        } catch (e: Exception) {
            LauncherLogger.error("Java runtime installation failed: ${e.message}")
            onStatus("Java install failed: ${e.message}")
            false
        }
    }
}
