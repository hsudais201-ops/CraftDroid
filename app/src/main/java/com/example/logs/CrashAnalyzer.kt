package com.example.logs

import java.io.File

data class CrashAnalysis(
    val exitCode: Int,
    val failureKind: LaunchFailureClassifier.Kind = LaunchFailureClassifier.Kind.UNKNOWN,
    val summary: String,
    val possibleCauses: List<String>,
    val recommendations: List<String>,
    val rawDetails: String
)

object CrashAnalyzer {

    fun analyze(exitCode: Int, logOutput: String, crashReportFile: File? = null): CrashAnalysis {
        val causes = mutableListOf<String>()
        val recommendations = mutableListOf<String>()
        var summary = "Minecraft process terminated with exit code $exitCode."

        val combinedText = buildString {
            append(logOutput)
            if (crashReportFile != null && crashReportFile.exists()) {
                append("\n--- CRASH REPORT ---\n")
                append(crashReportFile.readText())
            }
        }

        when {
            combinedText.contains("SIGSEGV") || combinedText.contains("A fatal error has been detected by the Java Runtime Environment") || combinedText.contains("Problematic frame:") -> {
                summary = "Minecraft crashed in native code or the graphics/runtime layer."
                causes.add("A native library, renderer, JVM component, or Android graphics bridge crashed.")
                causes.add("The HotSpot hs_err_pid log contains the native stack and problematic frame when available.")
                recommendations.add("Try another renderer (GL4ES/MobileGlues/Zink) and verify native libraries match the selected architecture.")
                recommendations.add("If the crash persists, inspect the saved HotSpot error log and crash diagnostics bundle.")
            }
            combinedText.contains("OutOfMemoryError") || combinedText.contains("java.lang.OutOfMemoryError") -> {
                summary = "Minecraft crashed due to Out of Memory (RAM exhaustion)."
                causes.add("Allocated RAM is too low for this Minecraft version or resource pack.")
                causes.add("Background applications consumed too much system memory.")
                recommendations.add("Increase RAM allocation in Settings (e.g. to 2048 MB or 3072 MB).")
                recommendations.add("Close unused background apps on your device.")
            }
            combinedText.contains("UnsupportedClassVersionError") || combinedText.contains("has been compiled by a more recent version of the Java Runtime") -> {
                summary = "Java version incompatibility detected."
                causes.add("This version of Minecraft requires a newer Java runtime (e.g. Java 17 or Java 21).")
                recommendations.add("Change the Java Runtime in Settings to match the version requirement.")
                recommendations.add("Run Java Runtime Manager to download the required JRE.")
            }
            combinedText.contains("UnsatisfiedLinkError") || combinedText.contains(".so: cannot open shared object file") || combinedText.contains("liblwjgl") -> {
                summary = "Native library linkage or graphics bridge failure."
                causes.add("Native OpenGL/LWJGL libraries for your CPU architecture could not be loaded.")
                causes.add("Natives may be missing, incomplete, or corrupted.")
                recommendations.add("Use [Repair Installation] to redownload native libraries.")
                recommendations.add("Switch graphics backend in Settings to Compatibility Mode.")
            }
            combinedText.contains("GL_INVALID_OPERATION") || combinedText.contains("Failed to create GLFW window") || combinedText.contains("GLFW error 65542") -> {
                summary = "Graphics initialization or GLFW display context failure."
                causes.add("The device GPU does not natively support the requested desktop OpenGL profile.")
                causes.add("GL4ES / Zink translation bridge needs compatibility flags enabled.")
                recommendations.add("Enable 'Compatibility Mode' in Settings under Graphics.")
                recommendations.add("Ensure device graphics drivers and Vulkan/GLES support are active.")
            }
            combinedText.contains("ClassNotFoundException") || combinedText.contains("NoClassDefFoundError") -> {
                summary = "Missing or corrupted Minecraft library file."
                causes.add("One or more required JAR libraries failed to download completely or is corrupt.")
                recommendations.add("Run [Repair Installation] to verify and redownload missing libraries.")
            }
            exitCode == 137 || exitCode == -9 -> {
                summary = "Process was killed by Android OS (OOM Killer)."
                causes.add("Device ran out of memory and Android system killed the Java process.")
                recommendations.add("Lower Minecraft RAM allocation so Android OS has headroom.")
                recommendations.add("Restart your Android device to free up cached memory.")
            }
            exitCode == 1 -> {
                causes.add("Generic Minecraft client error, missing argument, or mod incompatibility.")
                recommendations.add("Review full logs for specific mod or configuration exceptions.")
                recommendations.add("Try running a vanilla release without custom JVM arguments.")
            }
            else -> {
                causes.add("Unknown unexpected process termination.")
                recommendations.add("Check log file in Logs tab for detailed traceback.")
            }
        }

        val classified = LaunchFailureClassifier.classify(combinedText)
        if (classified.kind != LaunchFailureClassifier.Kind.UNKNOWN) {
            summary = classified.summary
            causes.add("Detected failure category: ${classified.kind}")
            classified.target?.let { causes.add("Affected component: $it") }
            recommendations.add(classified.action)
        }

        return CrashAnalysis(
            exitCode = exitCode,
            failureKind = classified.kind,
            summary = summary,
            possibleCauses = causes,
            recommendations = recommendations,
            rawDetails = combinedText.takeLast(4000)
        )
    }
}
