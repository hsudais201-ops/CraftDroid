package com.example.logs

import com.example.versions.VersionDetail
import java.io.File
import java.util.zip.ZipFile

/** Preflight checks that turn common JVM/classpath failures into actionable errors before JLI starts. */
object LaunchFailureGuard {
    data class Result(val valid: Boolean, val errors: List<String>, val warnings: List<String>)

    fun verifyClasspath(version: VersionDetail, librariesDir: File, clientJar: File): Result {
        val errors = mutableListOf<String>()
        val warnings = mutableListOf<String>()
        val jars = mutableListOf<File>()
        if (clientJar.isFile) jars += clientJar else errors += "Minecraft client JAR is missing"

        version.libraries.forEach { library ->
            library.artifact?.let { artifact ->
                val jar = File(librariesDir, artifact.path)
                if (!jar.isFile) errors += "Missing library: ${library.name} (${artifact.path})"
                else if (!jar.name.endsWith(".jar", true)) warnings += "Non-JAR library artifact: ${library.name}"
                else jars += jar
            }
        }

        val requiredClasses = linkedSetOf(version.mainClass)
        // Common loader entry points. If present in metadata, they must be on the resolved classpath.
        version.libraries.filter { it.name.contains("fabric-loader") || it.name.contains("modlauncher") }
            .forEach { lib ->
                if (lib.name.contains("fabric-loader")) requiredClasses += "net.fabricmc.loader.impl.launch.knot.KnotClient"
                if (lib.name.contains("modlauncher")) requiredClasses += "cpw.mods.modlauncher.Launcher"
            }

        val found = mutableSetOf<String>()
        for (jar in jars) {
            runCatching {
                ZipFile(jar).use { zip ->
                    for (entry in zip.entries()) {
                        if (!entry.isDirectory && entry.name.endsWith(".class")) found += entry.name.removeSuffix(".class").replace('/', '.')
                    }
                }
            }.onFailure { errors += "Cannot read library JAR ${jar.name}: ${it.message ?: "invalid ZIP"}" }
        }
        requiredClasses.filterNot { it in found }.forEach { errors += "Required class is missing from resolved classpath: $it" }

        return Result(errors.isEmpty(), errors, warnings)
    }
}
