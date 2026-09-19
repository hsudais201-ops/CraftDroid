package com.example.renderer

import com.example.logs.LauncherLogger
import com.example.versions.VersionDetail
import java.io.File
import java.util.zip.ZipFile

/**
 * Validates the Java-side LWJGL set before the embedded JVM is started.
 *
 * CraftDroid uses an Android GLFW implementation, so mixing unrelated LWJGL
 * versions is especially dangerous: GLFW method signatures and native loading
 * conventions can differ even when all JARs look valid individually.
 */
object LwjglCompatibilityValidator {
    data class Result(
        val valid: Boolean,
        val lwjglVersions: List<String>,
        val details: String
    )

    fun validate(version: VersionDetail, librariesDir: File, stubJar: File? = null): Result {
        val lwjglLibraries = version.libraries.filter {
            it.name.startsWith("org.lwjgl:")
        }

        if (lwjglLibraries.isEmpty()) {
            // Legacy versions may use lwjglx instead of modern LWJGL3.
            val legacy = version.libraries.any { it.name.startsWith("net.java.jinput:") || it.name.contains("lwjglx") }
            return if (legacy) {
                Result(true, emptyList(), "Legacy/non-LWJGL3 version; LWJGL3 compatibility check skipped")
            } else {
                Result(false, emptyList(), "No org.lwjgl libraries were found in version metadata")
            }
        }

        val versions = lwjglLibraries.mapNotNull { coordinateVersion(it.name) }.distinct()
        val malformed = lwjglLibraries.filter { coordinateVersion(it.name) == null }.map { it.name }
        if (malformed.isNotEmpty()) {
            return Result(false, versions, "Malformed LWJGL Maven coordinates: ${malformed.joinToString()}")
        }

        // All LWJGL artifacts for a Minecraft installation must resolve to one
        // release line. Mixing 3.2.x/3.3.x artifacts is a common source of
        // NoSuchMethodError and UnsatisfiedLinkError during GLFW initialization.
        val releaseLines = versions.map { it.substringBeforeLast('.') }.distinct()
        if (releaseLines.size > 1) {
            return Result(false, versions, "Mixed LWJGL release lines: ${releaseLines.joinToString()}")
        }

        val core = lwjglLibraries.firstOrNull { it.name == "org.lwjgl:lwjgl" }
        if (core == null) {
            return Result(false, versions, "LWJGL GLFW support exists but org.lwjgl:lwjgl core is missing")
        }

        if (stubJar != null) {
            val stubCheck = validateStubJar(stubJar)
            if (!stubCheck.first) return Result(false, versions, "GLFW stub incompatible: ${stubCheck.second}")
        }

        val nativeNames = lwjglLibraries.mapNotNull { it.nativesArtifact?.path }.filter { it.endsWith(".jar") }
        val mode = if (stubJar != null) "legacy Android GLFW Java stub" else "native GLFW backend"
        LauncherLogger.info(
            "LWJGL compatibility: versions=${versions.joinToString()} " +
                "core=${core.name} nativeArtifacts=${nativeNames.size} mode=$mode"
        )
        if (stubJar == null) {
            LauncherLogger.info("Modern LWJGL3 validation: CallbackBridge JNI is optional; native GLFW backend is authoritative")
        }
        return Result(true, versions, "LWJGL Java artifacts are internally consistent; $mode selected")
    }

    private fun coordinateVersion(name: String): String? {
        val parts = name.split(':')
        return if (parts.size >= 3 && parts[0] == "org.lwjgl" && parts[1].isNotBlank()) parts[2].takeIf { it.isNotBlank() } else null
    }

    private fun validateStubJar(file: File): Pair<Boolean, String> {
        if (!file.isFile) return false to "stub JAR does not exist"
        return runCatching {
            ZipFile(file).use { zip ->
                val glfw = zip.getEntry("org/lwjgl/glfw/GLFW.class")
                    ?: return false to "missing org/lwjgl/glfw/GLFW.class"
                val callback = zip.getEntry("org/lwjgl/glfw/CallbackBridge.class")
                    ?: return false to "missing CallbackBridge.class"
                val glfwBytes = zip.getInputStream(glfw).use { it.readBytes() }
                val callbackBytes = zip.getInputStream(callback).use { it.readBytes() }
                val glfwOk = glfwBytes.indexOf("glfwInit".toByteArray()) >= 0 &&
                    glfwBytes.indexOf("glfwPollEvents".toByteArray()) >= 0
                val callbackOk = listOf("receiveCallback", "nativeSendData", "nativeSetInputReady")
                    .all { callbackBytes.indexOf(it.toByteArray()) >= 0 }
                if (!glfwOk || !callbackOk) {
                    false to "required GLFW/CallbackBridge methods are missing"
                } else {
                    true to "OK"
                }
            }
        }.getOrElse { false to (it.message ?: "invalid stub JAR") }
    }
}
