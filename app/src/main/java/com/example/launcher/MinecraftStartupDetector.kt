package com.example.launcher

import com.example.logs.LauncherLogger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import java.io.File
import com.example.game.NativeGameBridge

/**
 * Step 55: observes the embedded Minecraft stdout/stderr log while JLI_Launch
 * is still running.  This does not require a child process or a PID because
 * Minecraft is embedded in the CraftDroid process.
 */
class MinecraftStartupDetector(
    private val scope: CoroutineScope,
    private val logFile: File,
    private val onPhase: (Phase) -> Unit = {}
) {
    enum class Phase(val label: String) {
        JVM_STARTING("JVM starting"),
        GAME_MAIN_STARTED("Minecraft main class started"),
        LWJGL_STARTED("LWJGL initialized"),
        OPENGL_STARTED("OpenGL renderer initialized"),
        AUDIO_STARTED("Audio initialized"),
        RESOURCES_STARTED("Minecraft resources initialized"),
        RENDERING("Minecraft render loop active"),
        MENU_READY_INFERRED("Minecraft client ready (menu state inferred)"),
        IN_GAME_DETECTED("Minecraft world/game state detected"),
        RUNNING("Minecraft runtime initialized"),
        FAILED("Minecraft startup failed"),
        EXITED("Minecraft exited")
    }

    private var job: Job? = null
    @Volatile private var phase: Phase = Phase.JVM_STARTING
    @Volatile private var failureText: String? = null
    @Volatile private var sawResourceInitialization = false
    @Volatile private var sawAudioInitialization = false
    @Volatile private var sawRenderLoop = false
    @Volatile private var sawWorldMarker = false
    @Volatile private var lastRenderFrameCount = 0L
    @Volatile private var lastRenderAdvanceAtMs = 0L

    fun start() {
        stop()
        phase = Phase.JVM_STARTING
        failureText = null
        sawResourceInitialization = false
        sawAudioInitialization = false
        sawRenderLoop = false
        sawWorldMarker = false
        lastRenderFrameCount = NativeGameBridge.renderFrameCount()
        lastRenderAdvanceAtMs = 0L
        onPhase(phase)
        job = scope.launch(Dispatchers.IO) {
            var offset = 0L
            var buffer = ""
            while (isActive) {
                try {
                    if (logFile.isFile) {
                        val length = logFile.length()
                        if (length < offset) offset = 0L
                        if (length > offset) {
                            java.io.RandomAccessFile(logFile, "r").use { raf ->
                                raf.seek(offset)
                                val bytes = ByteArray((length - offset).coerceAtMost(256 * 1024).toInt())
                                val read = raf.read(bytes)
                                if (read > 0) {
                                    offset += read
                                    buffer += String(bytes, 0, read, Charsets.UTF_8)
                                    if (buffer.length > 512 * 1024) buffer = buffer.takeLast(256 * 1024)
                                    process(buffer)
                                }
                            }
                        }
                    }
                } catch (t: Throwable) {
                    LauncherLogger.debug("Minecraft startup detector read error: ${t.message}")
                }
                delay(250)
            }
        }
    }

    private fun process(text: String) {
        val normalized = text.lowercase()
        val now = System.currentTimeMillis()
        val renderFrames = NativeGameBridge.renderFrameCount()
        if (renderFrames > lastRenderFrameCount) {
            sawRenderLoop = true
            lastRenderFrameCount = renderFrames
            lastRenderAdvanceAtMs = now
        }

        val worldMarker = listOf(
            "joining world", "joining ", "loading world", "loaded " ,
            "preparing spawn", "entering world", "respawn"
        ).any(normalized::contains)
        if (worldMarker) sawWorldMarker = true

        if (normalized.contains("reloading resourcemanager") ||
            normalized.contains("resource manager") ||
            normalized.contains("resource reload")) {
            sawResourceInitialization = true
        }
        if (normalized.contains("sound engine started") ||
            (normalized.contains("openal") && normalized.contains("initialized"))) {
            sawAudioInitialization = true
        }

        val detected = when {
            containsFailure(normalized) -> Phase.FAILED
            worldMarker && sawRenderLoop -> Phase.IN_GAME_DETECTED
            sawRenderLoop && sawResourceInitialization && sawAudioInitialization &&
                lastRenderAdvanceAtMs > 0L && now - lastRenderAdvanceAtMs < 3_000L -> Phase.RENDERING
            normalized.contains("openal") && (normalized.contains("device") || normalized.contains("sound engine") || normalized.contains("audio")) -> Phase.AUDIO_STARTED
            normalized.contains("opengl") && (normalized.contains("version") || normalized.contains("renderer") || normalized.contains("vendor")) -> Phase.OPENGL_STARTED
            normalized.contains("lwjgl") && (normalized.contains("version") || normalized.contains("3.")) -> Phase.LWJGL_STARTED
            normalized.contains("reload") && (normalized.contains("resourcemanager") || normalized.contains("resources")) -> Phase.RESOURCES_STARTED
            normalized.contains("setting user") || normalized.contains("minecraft main") || normalized.contains("game version") -> Phase.GAME_MAIN_STARTED
            normalized.contains("sound engine started") || normalized.contains("minecraft client started") || normalized.contains("done (") -> Phase.RUNNING
            else -> null
        }
        if (detected != null) advance(detected, text)

        // A title/menu screen has no universal log marker across all Minecraft
        // versions. Infer client-ready/menu state only after resources + audio
        // initialization and a live render loop are all observed, while no
        // world-loading marker has appeared. This is explicitly labeled inferred.
        if (!sawWorldMarker && sawRenderLoop && sawResourceInitialization && sawAudioInitialization &&
            (phase == Phase.RENDERING || phase == Phase.RUNNING) &&
            lastRenderAdvanceAtMs > 0L && now - lastRenderAdvanceAtMs < 3_000L) {
            advance(Phase.MENU_READY_INFERRED, "Live render loop + resource/audio initialization; no world marker observed")
        }
    }

    private fun containsFailure(text: String): Boolean {
        val patterns = listOf(
            "exception in thread",
            "noclassdeffounderror",
            "classnotfoundexception",
            "unsatisfiedlinkerror",
            "fatal error",
            "sigsegv",
            "failed to create glfw window",
            "could not load lwjgl",
            "error: unable to access jarfile",
            "outofmemoryerror"
        )
        return patterns.any(text::contains)
    }

    private fun advance(newPhase: Phase, source: String) {
        if (newPhase == phase && newPhase != Phase.FAILED) return
        if (newPhase.ordinal < phase.ordinal && newPhase != Phase.FAILED) return
        phase = newPhase
        if (newPhase == Phase.FAILED) failureText = source.takeLast(1200)
        LauncherLogger.info("Minecraft startup milestone: ${newPhase.label}")
        if (newPhase == Phase.FAILED) LauncherLogger.error("Minecraft startup failure detected in JVM output: ${failureText}")
        onPhase(newPhase)
    }

    fun currentPhase(): Phase = phase
    fun failureDetails(): String? = failureText

    fun stop(finalPhase: Phase? = null) {
        job?.cancel()
        job = null
        finalPhase?.let {
            phase = it
            onPhase(it)
        }
    }
}
