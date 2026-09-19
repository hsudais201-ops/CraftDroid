package com.example.launcher

import com.example.logs.LauncherLogger
import java.io.File
import java.util.zip.ZipFile

/** Fast, side-effect-free checks that catch common JVM classpath failures before startup. */
object LaunchPreflight {
    data class Result(val valid: Boolean, val errors: List<String>, val warnings: List<String>)

    fun verify(command: LaunchCommand, mainClass: String): Result {
        val errors = mutableListOf<String>()
        val warnings = mutableListOf<String>()
        val entries = command.classpathString.split(File.pathSeparator).filter { it.isNotBlank() }

        if (entries.isEmpty()) errors += "Minecraft classpath is empty."
        entries.forEach { path ->
            val file = File(path)
            if (!file.isFile || file.length() == 0L) errors += "Missing/empty classpath entry: $path"
        }

        val expected = mainClass.replace('.', '/') + ".class"
        var mainFound = false
        val duplicateNames = mutableMapOf<String, Int>()
        entries.filter { it.endsWith(".jar", true) }.forEach { path ->
            runCatching {
                ZipFile(path).use { zip ->
                    if (zip.getEntry(expected) != null) mainFound = true
                    val seen = HashSet<String>()
                    zip.entries().asSequence().forEach { entry ->
                        if (!entry.isDirectory && entry.name.endsWith(".class") && seen.add(entry.name)) {
                            if (entry.name == expected) duplicateNames[entry.name] = (duplicateNames[entry.name] ?: 0) + 1
                        }
                    }
                }
            }.onFailure { warnings += "Unable to inspect classpath JAR $path: ${it.message}" }
        }
        if (!mainFound) errors += "Main class $mainClass was not found in the resolved classpath."
        if ((duplicateNames[expected] ?: 0) > 1) warnings += "Main class $mainClass appears in multiple JARs; loader ordering may matter."

        if (errors.isEmpty()) LauncherLogger.info("Launch preflight passed: ${entries.size} classpath entries, main=$mainClass")
        else errors.forEach { LauncherLogger.error("Launch preflight: $it") }
        warnings.forEach { LauncherLogger.warn("Launch preflight: $it") }
        return Result(errors.isEmpty(), errors, warnings)
    }
}
