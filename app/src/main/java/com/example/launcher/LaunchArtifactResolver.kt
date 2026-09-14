package com.example.launcher

import com.example.downloader.HashVerifier
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.versions.LibraryArtifact
import com.example.versions.VersionDetail
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipFile

/**
 * Validates selected Minecraft library/native/client artifacts and rebuilds
 * a clean version-specific native directory from verified classifier JARs.
 */
object LaunchArtifactResolver {
    data class Result(
        val classpath: List<File>,
        val nativeJars: List<File>,
        val missing: List<String>,
        val corrupt: List<String>
    ) {
        val valid: Boolean get() = missing.isEmpty() && corrupt.isEmpty()
    }

    fun resolve(version: VersionDetail, fileSystem: MinecraftFileSystem): Result {
        val classpath = mutableListOf<File>()
        val nativeJars = mutableListOf<File>()
        val missing = mutableListOf<String>()
        val corrupt = mutableListOf<String>()

        version.libraries.forEach { library ->
            library.artifact?.let { artifact ->
                val file = File(fileSystem.librariesDir, artifact.path)
                checkArtifact(file, artifact, "library ${library.name}", missing, corrupt)
                if (file.isFile && file.length() > 0L) classpath += file
            }
            library.nativesArtifact?.let { artifact ->
                val file = File(fileSystem.librariesDir, artifact.path)
                checkArtifact(file, artifact, "native ${library.name}", missing, corrupt)
                if (file.isFile && file.length() > 0L) nativeJars += file
            }
        }

        val clientJar = fileSystem.getVersionJarFile(version.id)
        checkArtifact(clientJar, version.clientDownload.sha1, version.clientDownload.size,
            "Minecraft client ${version.id}", missing, corrupt)
        if (clientJar.isFile && clientJar.length() > 0L) classpath += clientJar

        return Result(
            classpath = classpath.distinctBy { it.absolutePath },
            nativeJars = nativeJars.distinctBy { it.absolutePath },
            missing = missing,
            corrupt = corrupt
        ).also { result ->
            result.missing.forEach { LauncherLogger.error("Launch artifact missing: $it") }
            result.corrupt.forEach { LauncherLogger.error("Launch artifact corrupt: $it") }
        }
    }

    fun rebuildNatives(version: VersionDetail, fileSystem: MinecraftFileSystem): File {
        val result = resolve(version, fileSystem)
        check(result.valid) {
            "Cannot rebuild natives before artifact validation: " +
                "missing=${result.missing.size}, corrupt=${result.corrupt.size}"
        }

        val output = fileSystem.getNativesDir(version.id)
        clearDirectory(output)
        output.mkdirs()
        version.libraries.forEach { library ->
            val artifact = library.nativesArtifact ?: return@forEach
            val jar = File(fileSystem.librariesDir, artifact.path)
            if (!result.nativeJars.any { it.absoluteFile == jar.absoluteFile }) return@forEach
            extractNativeJar(jar, output, library.extractExcludes)
        }
        return output
    }

    private fun checkArtifact(file: File, artifact: LibraryArtifact, label: String,
        missing: MutableList<String>, corrupt: MutableList<String>) =
        checkArtifact(file, artifact.sha1, artifact.size, label, missing, corrupt)

    private fun checkArtifact(file: File, expectedSha1: String, expectedSize: Long, label: String,
        missing: MutableList<String>, corrupt: MutableList<String>) {
        if (!file.isFile || file.length() == 0L) {
            missing += "$label -> ${file.absolutePath}"
            return
        }
        if (expectedSize > 0L && file.length() != expectedSize) {
            corrupt += "$label -> size ${file.length()} != $expectedSize"
            return
        }
        if (expectedSha1.length == 40 && !HashVerifier.verifySha1(file, expectedSha1)) {
            corrupt += "$label -> SHA-1 mismatch"
        }
    }

    private fun clearDirectory(directory: File) {
        if (!directory.exists()) return
        directory.listFiles()?.forEach { child ->
            if (child.isDirectory) clearDirectory(child)
            if (!child.delete()) error("Unable to delete native entry: ${child.absolutePath}")
        }
    }

    private fun extractNativeJar(jar: File, output: File, excludes: List<String>) {
        ZipFile(jar).use { zip ->
            zip.entries().asSequence().forEach { entry ->
                if (entry.isDirectory) return@forEach
                val name = entry.name.replace('\\', '/')
                if (!name.startsWith("META-INF/") && excludes.none { name.startsWith(it) }) {
                    val leaf = name.substringAfterLast('/')
                    if (leaf == name && (leaf.endsWith(".so") || leaf.endsWith(".dylib") || leaf.endsWith(".dll"))) {
                        val target = File(output, leaf)
                        FileOutputStream(target).use { out -> zip.getInputStream(entry).use { input -> input.copyTo(out) } }
                    }
                }
            }
        }
    }
}
