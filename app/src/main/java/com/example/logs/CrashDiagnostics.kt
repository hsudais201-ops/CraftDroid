package com.example.logs

import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/** Collects the most useful files produced by Minecraft/HotSpot after a crash. */
object CrashDiagnostics {
    data class Bundle(
        val crashReport: File?,
        val latestLog: File?,
        val hsErr: File?,
        val launcherLog: File?
    )

    fun collect(rootDir: File, jvmLog: File): Bundle {
        val crashReport = newest(rootDir.resolve("crash-reports"), "crash-*.txt")
        val latestLog = newest(rootDir.resolve("logs"), "*.log")
        val hsErr = newest(rootDir, "hs_err_pid*.log")
        val launcherLog = jvmLog.takeIf { it.isFile }
        return Bundle(crashReport, latestLog, hsErr, launcherLog)
    }

    fun findLatestHotSpotError(rootDir: File): File? =
        newest(rootDir, "hs_err_pid*.log")

    fun writeSummary(rootDir: File, exitCode: Int, bundle: Bundle): File? {
        return runCatching {
            val dir = rootDir.resolve("crash-diagnostics").apply { mkdirs() }
            val stamp = SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(Date())
            val out = File(dir, "diagnostic-$stamp.txt")
            out.printWriter().use { w ->
                w.println("CraftDroid crash diagnostics")
                w.println("Exit code: $exitCode")
                w.println("Crash report: ${bundle.crashReport?.absolutePath ?: "none"}")
                w.println("Minecraft log: ${bundle.latestLog?.absolutePath ?: "none"}")
                w.println("HotSpot error log: ${bundle.hsErr?.absolutePath ?: "none"}")
                w.println("JVM stdout/stderr: ${bundle.launcherLog?.absolutePath ?: "none"}")
                w.println()
                fun tail(file: File?, label: String) {
                    if (file == null || !file.isFile) return
                    w.println("===== $label =====")
                    val text = runCatching { file.readText() }.getOrDefault("")
                    w.println(text.takeLast(12000))
                }
                tail(bundle.crashReport, "CRASH REPORT")
                tail(bundle.hsErr, "HOTSPOT FATAL ERROR")
                tail(bundle.latestLog, "LATEST LOG")
                tail(bundle.launcherLog, "CRAFTDROID JVM OUTPUT")
            }
            out
        }.onFailure { LauncherLogger.error("Failed to write crash diagnostics: " + it.message) }.getOrNull()
    }

    private fun newest(dir: File, glob: String): File? {
        if (!dir.isDirectory) return null
        val regex = Regex(glob.replace(".", "\\.").replace("*", ".*"))
        return dir.listFiles()?.filter { it.isFile && regex.matches(it.name) }
            ?.maxByOrNull { it.lastModified() }
    }
}
