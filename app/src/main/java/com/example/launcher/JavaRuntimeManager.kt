package com.example.launcher

import android.content.Context
import java.io.BufferedInputStream
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import java.util.zip.GZIPInputStream

/**
 * Owns Java runtime selection, validation and installation state for the launcher.
 *
 * The launcher keeps runtimes inside its private files directory. Downloads are
 * metadata-driven and verified with size + SHA-256 before an archive is promoted
 * to an installed runtime. No runtime is executed before verification succeeds.
 */
class JavaRuntimeManager(private val context: Context) {

    data class RuntimeSpec(
        val major: Int,
        val url: String,
        val sha256: String,
        val archiveSize: Long
    )

    data class RuntimeInstallResult(
        val major: Int,
        val javaHome: File,
        val javaExecutable: File,
        val installed: Boolean,
        val message: String
    )

    companion object {
        private const val PREFS = "droid_launcher_runtime"
        private const val PREF_SELECTED = "selected_java_major"
        private const val PREF_VALIDATED = "validated_java_major"
        private const val MAX_REDIRECTS = 5
        private const val BUFFER_SIZE = 64 * 1024
        private const val CONNECT_TIMEOUT_MS = 15_000
        private const val READ_TIMEOUT_MS = 60_000
    }

    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val runtimeRoot = File(context.filesDir, "java-runtimes")
    private val installLocks = ConcurrentHashMap<Int, Any>()
    private val specs = ConcurrentHashMap<Int, RuntimeSpec>()

    init {
        runtimeRoot.mkdirs()
    }

    fun supportedMajors(): Set<Int> = setOf(8, 16, 17, 21, 25)

    fun selectedMajor(defaultMajor: Int = 17): Int {
        val selected = prefs.getInt(PREF_SELECTED, defaultMajor)
        return if (selected in supportedMajors()) selected else defaultMajor
    }

    fun setSelectedMajor(major: Int) {
        require(major in supportedMajors()) { "Unsupported Java runtime: $major" }
        prefs.edit().putInt(PREF_SELECTED, major).apply()
    }

    fun registerSpec(spec: RuntimeSpec) {
        require(spec.major in supportedMajors()) { "Unsupported Java runtime: ${spec.major}" }
        require(spec.url.startsWith("https://")) { "Runtime URL must use HTTPS" }
        require(spec.sha256.matches(Regex("[0-9a-fA-F]{64}"))) { "Runtime SHA-256 must be 64 hex characters" }
        require(spec.archiveSize > 0L) { "Runtime archive size must be positive" }
        specs[spec.major] = spec.copy(sha256 = spec.sha256.lowercase())
    }

    fun registerSpecs(values: Iterable<RuntimeSpec>) {
        values.forEach(::registerSpec)
    }

    /**
     * Resolves and installs a runtime when necessary. This method is intentionally
     * synchronous: callers should execute it from their existing IO coroutine.
     */
    fun ensureRuntime(requiredJava: Int): RuntimeInstallResult {
        require(requiredJava in supportedMajors()) { "Unsupported Java runtime: $requiredJava" }
        synchronized(installLocks.computeIfAbsent(requiredJava) { Any() }) {
            val home = runtimeRootFor(requiredJava)
            val executable = javaExecutableFor(home)
            if (isUsableJavaExecutable(executable)) {
                prefs.edit().putInt(PREF_VALIDATED, requiredJava).apply()
                return RuntimeInstallResult(requiredJava, home, executable, false, "Java $requiredJava already installed")
            }

            val spec = specs[requiredJava]
                ?: return RuntimeInstallResult(requiredJava, home, executable, false, "Java $requiredJava requires runtime metadata before download")

            val archive = File(runtimeRoot, "java-${requiredJava}.archive")
            downloadAndVerify(spec, archive)
            val staging = File(runtimeRoot, ".staging-$requiredJava-${System.nanoTime()}")
            try {
                staging.mkdirs()
                extractArchive(archive, staging)
                val extractedHome = findJavaHome(staging)
                    ?: throw IOException("Java $requiredJava archive contains no executable runtime")
                val finalHome = runtimeRootFor(requiredJava)
                if (finalHome.exists()) finalHome.deleteRecursively()
                if (!extractedHome.renameTo(finalHome)) {
                    copyRecursively(extractedHome, finalHome)
                    extractedHome.deleteRecursively()
                }
                val finalExecutable = javaExecutableFor(finalHome)
                if (!isUsableJavaExecutable(finalExecutable)) {
                    finalHome.deleteRecursively()
                    throw IOException("Java $requiredJava installation failed validation")
                }
                prefs.edit().putInt(PREF_VALIDATED, requiredJava).apply()
                return RuntimeInstallResult(requiredJava, finalHome, finalExecutable, true, "Java $requiredJava installed and verified")
            } finally {
                staging.deleteRecursively()
            }
        }
    }

    fun isInstalled(major: Int): Boolean {
        if (major !in supportedMajors()) return false
        return isUsableJavaExecutable(javaExecutableFor(runtimeRootFor(major)))
    }

    fun isValidated(major: Int): Boolean = prefs.getInt(PREF_VALIDATED, -1) == major && isInstalled(major)

    fun runtimeHome(major: Int): File = runtimeRootFor(major)

    private fun runtimeRootFor(major: Int): File = File(runtimeRoot, major.toString())

    private fun javaExecutableFor(home: File): File = File(home, "bin/java")

    private fun isUsableJavaExecutable(file: File): Boolean = file.isFile && file.canRead() && file.length() > 0L

    private fun downloadAndVerify(spec: RuntimeSpec, destination: File) {
        destination.parentFile?.mkdirs()
        var connection: HttpURLConnection? = null
        var current = spec.url
        var redirects = 0
        try {
            while (true) {
                connection = (URL(current).openConnection() as HttpURLConnection).apply {
                    connectTimeout = CONNECT_TIMEOUT_MS
                    readTimeout = READ_TIMEOUT_MS
                    instanceFollowRedirects = false
                    setRequestProperty("User-Agent", "DroidLauncher/1.0")
                }
                when (val code = connection.responseCode) {
                    in 300..399 -> {
                        if (++redirects > MAX_REDIRECTS) throw IOException("Too many runtime download redirects")
                        current = connection.getHeaderField("Location") ?: throw IOException("Runtime redirect missing Location")
                        if (!current.startsWith("https://")) throw IOException("Runtime redirect is not HTTPS")
                        connection.disconnect()
                        continue
                    }
                    200 -> break
                    else -> throw IOException("Runtime download HTTP $code")
                }
            }

            val temp = File(destination.parentFile, destination.name + ".part")
            FileOutputStream(temp).use { output ->
                BufferedInputStream(connection!!.inputStream, BUFFER_SIZE).use { input ->
                    val buffer = ByteArray(BUFFER_SIZE)
                    var total = 0L
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        if (total > spec.archiveSize * 2L) throw IOException("Runtime archive exceeds declared size")
                        output.write(buffer, 0, read)
                    }
                }
            }
            if (temp.length() != spec.archiveSize) throw IOException("Runtime archive size mismatch")
            if (!sha256(temp).equals(spec.sha256, ignoreCase = true)) throw IOException("Runtime SHA-256 mismatch")
            if (destination.exists()) destination.delete()
            if (!temp.renameTo(destination)) throw IOException("Unable to promote verified runtime archive")
        } finally {
            connection?.disconnect()
            val partial = File(destination.parentFile, destination.name + ".part")
            if (partial.exists()) partial.delete()
        }
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        FileInputStream(file).use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                digest.update(buffer, 0, count)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun extractArchive(archive: File, target: File) {
        // Runtime archives are deliberately handled without external executables.
        // A tar reader can be supplied by the project when its native/runtime layer
        // supports it; ZIP is used for the portable JVM bundles currently packaged.
        if (archive.name.endsWith(".zip")) {
            java.util.zip.ZipInputStream(FileInputStream(archive)).use { input ->
                val buffer = ByteArray(BUFFER_SIZE)
                while (true) {
                    val entry = input.nextEntry ?: break
                    val clean = entry.name.replace('\\', '/')
                    if (clean.startsWith("/") || clean.contains("../")) throw IOException("Unsafe runtime archive path")
                    val out = File(target, clean)
                    if (!out.canonicalPath.startsWith(target.canonicalPath + File.separator)) throw IOException("Runtime archive path escapes staging directory")
                    if (entry.isDirectory) out.mkdirs() else {
                        out.parentFile?.mkdirs()
                        FileOutputStream(out).use { output ->
                            while (true) {
                                val count = input.read(buffer)
                                if (count < 0) break
                                output.write(buffer, 0, count)
                            }
                        }
                    }
                }
            }
            return
        }

        if (archive.name.endsWith(".tar.gz") || archive.name.endsWith(".tgz")) {
            throw IOException("tar.gz runtime extraction is delegated to the platform runtime installer")
        }
        throw IOException("Unsupported Java runtime archive format: ${archive.name}")
    }

    private fun findJavaHome(staging: File): File? {
        val candidates = mutableListOf<File>()
        fun visit(dir: File, depth: Int) {
            if (depth > 4) return
            if (!dir.isDirectory) return
            if (File(dir, "bin/java").isFile) candidates += dir
            dir.listFiles()?.forEach { visit(it, depth + 1) }
        }
        visit(staging, 0)
        return candidates.firstOrNull { isUsableJavaExecutable(File(it, "bin/java")) }
    }

    private fun copyRecursively(source: File, destination: File) {
        if (source.isDirectory) {
            destination.mkdirs()
            source.listFiles()?.forEach { copyRecursively(it, File(destination, it.name)) }
        } else {
            destination.parentFile?.mkdirs()
            FileInputStream(source).use { input -> FileOutputStream(destination).use { output -> input.copyTo(output) } }
        }
    }
}
