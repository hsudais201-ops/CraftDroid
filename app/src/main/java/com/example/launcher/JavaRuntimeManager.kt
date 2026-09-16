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
import java.util.zip.GZIPInputStream
import java.util.zip.ZipInputStream

/**
 * Owns Java runtime selection, validation and installation state for the launcher.
 * Runtimes are kept inside the application's private files directory and are only
 * promoted after HTTPS download, exact-size and SHA-256 verification.
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
        private const val MAX_ARCHIVE_MULTIPLIER = 2L
        private const val TAR_BLOCK = 512
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

    /** Execute from the launch/install coroutine; it performs blocking file/network I/O. */
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

            val extension = archiveExtension(spec.url)
            val archive = File(runtimeRoot, "java-${requiredJava}$extension")
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
                archive.delete()
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

    private fun isUsableJavaExecutable(file: File): Boolean {
        return file.isFile && file.canRead() && file.length() > 0L && file.setExecutable(true, false)
    }

    private fun archiveExtension(url: String): String = when {
        url.contains(".tar.gz", ignoreCase = true) -> ".tar.gz"
        url.contains(".tgz", ignoreCase = true) -> ".tgz"
        url.contains(".zip", ignoreCase = true) -> ".zip"
        else -> ".archive"
    }

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
                        if (total > spec.archiveSize * MAX_ARCHIVE_MULTIPLIER) throw IOException("Runtime archive exceeds safe declared-size limit")
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
        return digest.digest().joinToString("") { byte ->
            "%02x".format(byte.toInt() and 0xff)
        }
    }

    private fun extractArchive(archive: File, target: File) {
        when {
            archive.name.endsWith(".zip", ignoreCase = true) -> extractZip(archive, target)
            archive.name.endsWith(".tar.gz", ignoreCase = true) || archive.name.endsWith(".tgz", ignoreCase = true) -> {
                extractTarGz(archive, target)
            }
            else -> throw IOException("Unsupported Java runtime archive format: ${archive.name}")
        }
    }

    private fun extractZip(archive: File, target: File) {
        ZipInputStream(FileInputStream(archive)).use { input ->
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                val entry = input.nextEntry ?: break
                writeArchiveEntry(entry.name, entry.isDirectory, target, input, buffer)
            }
        }
    }

    private fun extractTarGz(archive: File, target: File) {
        GZIPInputStream(BufferedInputStream(FileInputStream(archive), BUFFER_SIZE), BUFFER_SIZE).use { input ->
            val header = ByteArray(TAR_BLOCK)
            val buffer = ByteArray(BUFFER_SIZE)
            while (true) {
                readFully(input, header)
                if (header.all { it.toInt() == 0 }) break
                val name = tarString(header, 0, 100)
                val prefix = tarString(header, 345, 155)
                val entryName = if (prefix.isEmpty()) name else "$prefix/$name"
                val size = parseTarOctal(header, 124, 12)
                val type = header[156].toInt().toChar()
                when (type) {
                    '5' -> writeArchiveEntry(entryName, true, target, input, buffer)
                    '0', '\u0000' -> writeTarFile(entryName, size, target, input, buffer)
                    else -> skipFully(input, roundUpTar(size))
                }
            }
        }
    }

    private fun writeArchiveEntry(
        name: String,
        directory: Boolean,
        target: File,
        input: java.io.InputStream,
        buffer: ByteArray
    ) {
        val clean = name.replace('\\', '/')
        if (clean.startsWith("/") || clean.split('/').any { it == ".." }) throw IOException("Unsafe runtime archive path")
        val canonicalTarget = target.canonicalPath + File.separator
        val out = File(target, clean)
        if (!out.canonicalPath.startsWith(canonicalTarget)) throw IOException("Runtime archive path escapes staging directory")
        if (directory) {
            out.mkdirs()
        } else {
            out.parentFile?.mkdirs()
            FileOutputStream(out).use { output ->
                while (true) {
                    val count = input.read(buffer)
                    if (count < 0) break
                    output.write(buffer, 0, count)
                }
            }
            out.setExecutable(true, false)
        }
    }

    private fun writeTarFile(
        name: String,
        size: Long,
        target: File,
        input: java.io.InputStream,
        buffer: ByteArray
    ) {
        if (size < 0L) throw IOException("Negative tar entry size")
        val clean = name.replace('\\', '/')
        if (clean.startsWith("/") || clean.split('/').any { it == ".." }) throw IOException("Unsafe runtime tar path")
        val canonicalTarget = target.canonicalPath + File.separator
        val out = File(target, clean)
        if (!out.canonicalPath.startsWith(canonicalTarget)) throw IOException("Runtime tar path escapes staging directory")
        out.parentFile?.mkdirs()
        FileOutputStream(out).use { output ->
            var remaining = size
            while (remaining > 0) {
                val read = input.read(buffer, 0, minOf(buffer.size.toLong(), remaining).toInt())
                if (read < 0) throw IOException("Unexpected end of tar archive")
                output.write(buffer, 0, read)
                remaining -= read
            }
        }
        out.setExecutable(true, false)
        val padding = roundUpTar(size) - size
        if (padding > 0) skipFully(input, padding)
    }

    private fun findJavaHome(staging: File): File? {
        val candidates = mutableListOf<File>()
        fun visit(dir: File, depth: Int) {
            if (depth > 5 || !dir.isDirectory) return
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
            if (source.canExecute()) destination.setExecutable(true, false)
        }
    }

    private fun readFully(input: java.io.InputStream, buffer: ByteArray) {
        var offset = 0
        while (offset < buffer.size) {
            val count = input.read(buffer, offset, buffer.size - offset)
            if (count < 0) throw IOException("Unexpected end of tar header")
            offset += count
        }
    }

    private fun skipFully(input: java.io.InputStream, length: Long) {
        var remaining = length
        while (remaining > 0) {
            val skipped = input.skip(remaining)
            if (skipped > 0) remaining -= skipped else {
                if (input.read() < 0) throw IOException("Unexpected end of runtime archive")
                remaining--
            }
        }
    }

    private fun roundUpTar(size: Long): Long = ((size + TAR_BLOCK - 1L) / TAR_BLOCK) * TAR_BLOCK

    private fun tarString(bytes: ByteArray, offset: Int, length: Int): String {
        var end = offset
        val limit = offset + length
        while (end < limit && bytes[end].toInt() != 0) end++
        return bytes.copyOfRange(offset, end).toString(Charsets.UTF_8).trim()
    }

    private fun parseTarOctal(bytes: ByteArray, offset: Int, length: Int): Long {
        var value = 0L
        var seenDigit = false
        for (i in offset until offset + length) {
            val c = bytes[i].toInt() and 0xff
            if (c == 0 || c == 32) continue
            if (c !in 48..55) break
            seenDigit = true
            value = value * 8L + (c - 48)
        }
        return if (seenDigit) value else 0L
    }
}
