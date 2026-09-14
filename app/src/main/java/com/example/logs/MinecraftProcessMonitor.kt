package com.example.logs

import com.example.game.NativeGameBridge
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.File

/** Observes the embedded Minecraft JVM without owning or force-killing it. */
class MinecraftProcessMonitor(
    private val logFile: File,
    private val diagnosticsDir: File,
    private val onEvent: (Event) -> Unit = {}
) {
    enum class EventType {
        JVM_STARTING, JVM_RUNNING, LWJGL_READY, RESOURCE_READY, AUDIO_READY, MENU_READY, IN_GAME,
        CLASS_MISSING, NATIVE_LINK_FAILURE, GLFW_FAILURE, JAVA_VERSION_FAILURE, MEMORY_FAILURE,
        MOD_FAILURE, JVM_NATIVE_CRASH, LOG_CHANGED, JVM_STOPPED, MONITOR_TIMEOUT
    }

    data class Event(val type: EventType, val message: String, val timestampMs: Long = System.currentTimeMillis())

    private var job: Job? = null

    fun start(scope: CoroutineScope = CoroutineScope(Dispatchers.IO)) {
        stop()
        job = scope.launch(Dispatchers.IO) { monitorLoop() }
    }

    fun stop() {
        job?.cancel()
        job = null
    }

    private suspend fun monitorLoop() {
        diagnosticsDir.mkdirs()
        var offset = 0L
        var lwjglReady = false
        var resourceReady = false
        var audioReady = false
        var inGame = false
        var menuReady = false
        var lastObservedState = -1
        var lastFrameCount = NativeGameBridge.renderFrameCount()
        var lastProgressAt = System.currentTimeMillis()
        val startedAt = System.currentTimeMillis()
        emit(EventType.JVM_STARTING, "Embedded Minecraft JVM monitor started")

        while (kotlinx.coroutines.currentCoroutineContext().isActive) {
            val now = System.currentTimeMillis()
            readNewLogLines(offset) { chunk, newOffset ->
                offset = newOffset
                if (chunk.isBlank()) return@readNewLogLines
                emit(EventType.LOG_CHANGED, "${chunk.length} bytes of Minecraft output captured")
                val lower = chunk.lowercase()
                classifyFailure(lower)?.let { emit(it.first, it.second) }
                if (!lwjglReady && (("lwjgl" in lower && ("initialized" in lower || "version" in lower)) || "opengl version" in lower)) {
                    lwjglReady = true; emit(EventType.LWJGL_READY, "Minecraft reached LWJGL/OpenGL initialization")
                }
                if (!resourceReady && ("reloading resourcemanager" in lower || "resource reload" in lower || "resource manager" in lower)) {
                    resourceReady = true; emit(EventType.RESOURCE_READY, "Minecraft resource system initialized")
                }
                if (!audioReady && ("sound engine started" in lower || ("openal" in lower && "initialized" in lower))) {
                    audioReady = true; emit(EventType.AUDIO_READY, "Minecraft audio system initialized")
                }
                if ("joining world" in lower || "loading world" in lower || "preparing spawn" in lower || "entering world" in lower) {
                    if (!inGame) { inGame = true; emit(EventType.IN_GAME, "Minecraft world/in-game state detected") }
                }
            }

            val state = NativeGameBridge.javaState()
            if (state != lastObservedState) {
                lastObservedState = state
                if (state == 2) emit(EventType.JVM_RUNNING, "Embedded Minecraft JVM entered RUNNING state")
                if (state == 4) { emit(EventType.JVM_STOPPED, "Embedded Minecraft JVM exited"); return }
            }
            if (!menuReady && !inGame && lwjglReady && resourceReady && audioReady && now - startedAt >= 1500L) {
                menuReady = true; emit(EventType.MENU_READY, "Minecraft menu readiness inferred from renderer + resources + audio")
            }

            val frames = NativeGameBridge.renderFrameCount()
            if (frames > lastFrameCount) { lastFrameCount = frames; lastProgressAt = now }
            else if (lwjglReady && now - lastProgressAt >= 8_000L) {
                emit(EventType.GLFW_FAILURE, "Renderer heartbeat stalled for at least 8 seconds; investigate GLFW/EGL/native graphics logs")
                lastProgressAt = now
            }
            if (state == 0 && now - startedAt >= 120_000L) {
                emit(EventType.MONITOR_TIMEOUT, "Minecraft monitor reached its 120-second observation window"); return
            }
            delay(250L)
        }
    }

    private fun readNewLogLines(currentOffset: Long, consumer: (String, Long) -> Unit) {
        if (!logFile.isFile) return
        runCatching {
            val length = logFile.length()
            if (length <= currentOffset) return
            logFile.inputStream().use { input ->
                var skipped = input.skip(currentOffset)
                while (skipped < currentOffset) {
                    val more = input.skip(currentOffset - skipped)
                    if (more <= 0) break
                    skipped += more
                }
                consumer(input.readBytes().toString(Charsets.UTF_8), length)
            }
        }.onFailure { LauncherLogger.warn("Minecraft process monitor could not read log: ${it.message}") }
    }

    private fun classifyFailure(text: String): Pair<EventType, String>? = when {
        "classnotfoundexception" in text || "noclassdeffounderror" in text -> EventType.CLASS_MISSING to "Java classpath failure detected"
        "unsatisfiedlinkerror" in text || "cannot open shared object file" in text || "dlopen failed" in text -> EventType.NATIVE_LINK_FAILURE to "Native library linkage failure detected"
        "failed to create glfw" in text || "glfw error" in text -> EventType.GLFW_FAILURE to "GLFW initialization failure detected"
        "unsupportedclassversionerror" in text || "more recent version of the java runtime" in text -> EventType.JAVA_VERSION_FAILURE to "Java runtime/class version mismatch detected"
        "outofmemoryerror" in text || "java heap space" in text || "killed by android" in text -> EventType.MEMORY_FAILURE to "Memory exhaustion detected"
        (("fabric" in text && ("loader" in text || "knotclient" in text)) || ("forge" in text && ("mod" in text || "loader" in text))) -> EventType.MOD_FAILURE to "Mod-loader startup failure detected"
        "sigsegv" in text || "sigabrt" in text || "problematic frame:" in text || "fatal error has been detected by the java runtime environment" in text -> EventType.JVM_NATIVE_CRASH to "JVM/native crash signature detected"
        else -> null
    }

    private fun emit(type: EventType, message: String) {
        val event = Event(type, message)
        onEvent(event)
        runCatching {
            diagnosticsDir.mkdirs()
            File(diagnosticsDir, "step165-events.log").appendText("${event.timestampMs} [${event.type}] ${event.message}\n")
        }
        when (type) {
            EventType.CLASS_MISSING, EventType.NATIVE_LINK_FAILURE, EventType.GLFW_FAILURE,
            EventType.JAVA_VERSION_FAILURE, EventType.MEMORY_FAILURE, EventType.MOD_FAILURE,
            EventType.JVM_NATIVE_CRASH -> LauncherLogger.error(message)
            else -> LauncherLogger.info(message)
        }
    }
}
