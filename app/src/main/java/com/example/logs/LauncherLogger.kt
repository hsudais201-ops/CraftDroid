package com.example.logs

import android.content.Context
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.io.File
import java.io.FileWriter
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CopyOnWriteArrayList

enum class LogLevel {
    INFO, WARN, ERROR, DEBUG, MINECRAFT
}

data class LogEntry(
    val timestamp: Long = System.currentTimeMillis(),
    val level: LogLevel,
    val message: String
) {
    fun format(): String {
        val date = SimpleDateFormat("HH:mm:ss", Locale.US).format(Date(timestamp))
        return "[$date] [${level.name}] $message"
    }
}

object LauncherLogger {
    private val _logs = MutableStateFlow<List<LogEntry>>(emptyList())
    val logs: StateFlow<List<LogEntry>> = _logs.asStateFlow()

    private val logBuffer = CopyOnWriteArrayList<LogEntry>()
    private var logFile: File? = null
    private val maxBuffer = 2000

    fun init(context: Context) {
        try {
            val logsDir = File(context.getExternalFilesDir(null) ?: context.filesDir, "Minecraft/logs")
            logsDir.mkdirs()
            val filename = "launcher-${SimpleDateFormat("yyyy-MM-dd-HHmmss", Locale.US).format(Date())}.log"
            logFile = File(logsDir, filename)
            info("Launcher logger initialized. Log file: ${logFile?.name}")
        } catch (e: Exception) {
            android.util.Log.e("LauncherLogger", "Failed to init log file", e)
        }
    }

    fun log(level: LogLevel, rawMessage: String) {
        // Redact tokens or sensitive strings
        val sanitized = sanitize(rawMessage)
        val entry = LogEntry(level = level, message = sanitized)

        logBuffer.add(entry)
        if (logBuffer.size > maxBuffer) {
            logBuffer.removeAt(0)
        }
        _logs.value = logBuffer.toList()

        // Write to disk
        try {
            logFile?.let { file ->
                FileWriter(file, true).use { writer ->
                    writer.appendLine(entry.format())
                }
            }
        } catch (e: Exception) {
            android.util.Log.w("MCLauncher", "Could not write launcher log file: " + e.message)
        }

        when (level) {
            LogLevel.INFO -> android.util.Log.i("MCLauncher", sanitized)
            LogLevel.WARN -> android.util.Log.w("MCLauncher", sanitized)
            LogLevel.ERROR -> android.util.Log.e("MCLauncher", sanitized)
            LogLevel.DEBUG -> android.util.Log.d("MCLauncher", sanitized)
            LogLevel.MINECRAFT -> android.util.Log.v("MinecraftProcess", sanitized)
        }
    }

    fun info(msg: String) = log(LogLevel.INFO, msg)
    fun warn(msg: String) = log(LogLevel.WARN, msg)
    fun error(msg: String) = log(LogLevel.ERROR, msg)
    fun debug(msg: String) = log(LogLevel.DEBUG, msg)
    fun game(msg: String) = log(LogLevel.MINECRAFT, msg)

    fun clear() {
        logBuffer.clear()
        _logs.value = emptyList()
    }

    fun getLogsAsText(): String {
        return logBuffer.joinToString("\n") { it.format() }
    }

    private fun sanitize(input: String): String {
        var s = input
        // Redact access tokens (UUIDs, JWTs, OAuth tokens)
        s = s.replace(Regex("""(accessToken|access_token|refresh_token|Token|token|client_secret)=([^\s&,]+)""")) {
            "${it.groupValues[1]}=[REDACTED]"
        }
        s = s.replace(Regex("""(bearer|Bearer)\s+[A-Za-z0-9-_.]+""")) {
            "Bearer [REDACTED]"
        }
        s = s.replace(Regex("""XBL3\.0\s+x=[^;]+;[^\s]+""")) {
            "XBL3.0 [REDACTED_TICKET]"
        }
        return s
    }
}
