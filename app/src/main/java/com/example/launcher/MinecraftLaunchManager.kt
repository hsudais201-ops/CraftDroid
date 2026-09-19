package com.example.launcher

import com.example.auth.AccountManager
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.CrashAnalysis
import com.example.logs.CrashAnalyzer
import com.example.logs.LauncherLogger
import android.view.Surface
import com.example.game.NativeGameBridge
import com.example.renderer.RendererBackend
import com.example.renderer.LwjglGlfwStubManager
import com.example.renderer.RendererManager
import com.example.minecraft.ModCompatibilityManager
import com.example.runtime.JavaRuntimeManager
import com.example.settings.SettingsRepository
import com.example.versions.VersionJsonParser
import com.example.versions.VersionInheritanceResolver
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.withTimeout
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.async
import kotlinx.coroutines.CancellationException
import java.io.File
import java.util.concurrent.atomic.AtomicBoolean

sealed class LaunchState {
    data object Idle : LaunchState()
    data class Preparing(val currentStep: Int, val stepName: String, val details: String) : LaunchState()
    data class Running(val startTimeMs: Long, val versionId: String, val pid: Long = 0L) : LaunchState()
    data class Exited(val sessionDurationMs: Long, val exitCode: Int, val crashAnalysis: CrashAnalysis?) : LaunchState()
    data class Error(val message: String) : LaunchState()
}

class MinecraftLaunchManager(
    private val fileSystem: MinecraftFileSystem,
    private val accountManager: AccountManager,
    private val javaManager: JavaRuntimeManager,
    private val rendererManager: RendererManager,
    private val commandBuilder: LaunchCommandBuilder,
    private val versionParser: VersionJsonParser,
    private val settingsRepository: SettingsRepository,
    private val lwjglGlfwStubManager: LwjglGlfwStubManager,
    private val versionInheritanceResolver: VersionInheritanceResolver,
    private val modCompatibilityManager: ModCompatibilityManager,
    private val installationRepairManager: com.example.minecraft.InstallationRepairManager,
    private val appScope: CoroutineScope
) {

    private val _state = MutableStateFlow<LaunchState>(LaunchState.Idle)
    val state: StateFlow<LaunchState> = _state.asStateFlow()

    private var runningProcess: Process? = null
    private var launchJob: Job? = null
    @Volatile private var javaLaunchActive = false
    @Volatile private var surfaceReady = CompletableDeferred<Unit>()
    @Volatile private var lastSurface: Surface? = null
    @Volatile private var lastSurfaceWidth: Int = 0
    @Volatile private var lastSurfaceHeight: Int = 0
    private val stopRequestInFlight = AtomicBoolean(false)

    fun launch(
        versionId: String,
        uuid: String,
        ramMb: Int,
        rendererBackend: RendererBackend,
        customJvmArgs: String,
        serverHost: String? = null,
        serverPort: Int? = null
    ) {
        // Never cancel/replace an existing launch job while an embedded JVM is
        // active. JLI_Launch runs inside this process (not as a child Process),
        // and cancelling the coroutine cannot safely terminate that native call.
        // Starting another launch concurrently could then race the native bridge
        // and corrupt the Android GLFW/EGL or JVM lifecycle state.
        if (javaLaunchActive || NativeGameBridge.isJavaRunning()) {
            LauncherLogger.warn("Minecraft launch rejected: an embedded JVM launch is already active (state=${NativeGameBridge.javaState()}).")
            _state.value = LaunchState.Error("Minecraft is already running or starting. Stop the current session before launching another one.")
            return
        }
        launchJob?.cancel()
        // GameActivity is normally created after LaunchState enters Running, but a
        // relaunch can occur while the previous GameActivity/surface is still alive
        // (for example after a natural Minecraft exit). Seed the readiness gate from
        // the current native surface so the new launch does not wait 20 seconds for
        // a callback that has already happened.
        surfaceReady = CompletableDeferred()
        val currentSurfaceHandle = NativeGameBridge.surfaceHandle()
        if (currentSurfaceHandle != 0L &&
            NativeGameBridge.surfaceWidth() > 0 &&
            NativeGameBridge.surfaceHeight() > 0
        ) {
            surfaceReady.complete(Unit)
            LauncherLogger.info("Launch surface gate already satisfied by existing Android Surface handle=$currentSurfaceHandle")
        }
        launchJob = appScope.launch {
            try {
                // Step 1: Checking account with provider-specific launch validation
                _state.value = LaunchState.Preparing(1, "Checking account", "Verifying account credentials & profile...")
                LauncherLogger.info("Step 1/6: Checking active account credentials for UUID $uuid...")

                val currentSettings = settingsRepository.settingsFlow.first()
                val validatedAccount = accountManager.validateAccountForLaunch(
                    uuid = uuid,
                    allowLocalTestMode = true
                ).getOrThrow()

                val username = validatedAccount.username
                val isOfflineAccount = validatedAccount.isLocalTestProfile
                val accessToken = if (isOfflineAccount) {
                    // Offline/local profiles use the conventional local session marker.
                    // This is not a Microsoft/Xbox authentication token.
                    "0"
                } else {
                    accountManager.getValidAccessToken(uuid)
                        ?: throw IllegalStateException("Your ${validatedAccount.providerType} session has expired. Please sign in again.")
                }
                LauncherLogger.info("Account validated for launch: $username (${validatedAccount.providerType})")

                // Step 2: Checking Minecraft files
                _state.value = LaunchState.Preparing(2, "Checking Minecraft files", "Validating version JSON and client JAR...")
                LauncherLogger.info("Step 2/6: Checking Minecraft files for version $versionId...")
                val versionJsonFile = fileSystem.getVersionJsonFile(versionId)
                val clientJar = fileSystem.getVersionJarFile(versionId)
                if (!versionJsonFile.exists() || !clientJar.exists()) {
                    throw IllegalStateException("Minecraft $versionId files are missing. Please download or repair.")
                }
                val resolvedVersionJson = versionInheritanceResolver.resolve(versionId, versionJsonFile.readText())
                val versionDetail = versionParser.parseVersionDetail(resolvedVersionJson)

                // Step 2a: Scan enabled mods without executing any mod code.
                // This catches obvious loader/version mismatches before the JVM starts.
                val modCheck = modCompatibilityManager.validate(versionDetail)
                LauncherLogger.info(
                    "Mod scan: loader=${modCheck.loader}, scanned=${modCheck.scanned}, " +
                        "enabled=${modCheck.enabled}, valid=${modCheck.valid}"
                )
                modCheck.warnings.take(5).forEach { LauncherLogger.warn(it) }
                if (!modCheck.valid) {
                    throw IllegalStateException(
                        "Mod compatibility check failed: ${modCheck.errors.take(5).joinToString("; ")}. " +
                            "Disable or replace the incompatible mod(s) and try again."
                    )
                }

                // Step 2b: Verify every required on-disk artifact before starting the JVM.
                // This catches truncated downloads, corrupt assets and missing native archives
                // before they turn into opaque LWJGL/Minecraft crashes.
                var installCheck = com.example.minecraft.GameInstallationVerifier(fileSystem).verify(versionDetail)
                if (!installCheck.valid) {
                    LauncherLogger.warn("Installation verification failed; attempting selective Step 38 repair…")
                    val repair = installationRepairManager.repair(versionDetail)
                    LauncherLogger.info("Step 38 repair result: ${repair.summary}")
                    repair.failed.take(8).forEach { LauncherLogger.warn("Repair failure: $it") }
                    installCheck = com.example.minecraft.GameInstallationVerifier(fileSystem).verify(versionDetail)
                    if (!installCheck.valid) {
                        throw IllegalStateException(
                            "Minecraft $versionId is still incomplete after automatic repair. " +
                                "${installCheck.errors.take(3).joinToString("; ")}. Open the installation repair screen or reinstall the version."
                        )
                    }
                }

                // Step 3: Checking Java
                _state.value = LaunchState.Preparing(3, "Checking Java", "Detecting compatible OpenJDK runtime...")
                LauncherLogger.info("Step 3/6: Checking Java requirement (${versionDetail.javaVersion.majorVersion})...")
                val requiredJava = versionDetail.javaVersion.majorVersion
                LauncherLogger.info("Minecraft ${versionDetail.id} declares Java $requiredJava")
                if (requiredJava !in setOf(8, 16, 17, 21, 25)) {
                    throw IllegalStateException(
                        "Minecraft ${versionDetail.id} requires unsupported Java $requiredJava. " +
                            "Install a compatible Android JRE before launching this version."
                    )
                }
                val javaRuntime = javaManager.ensureRuntime(requiredJava) { status ->
                    LauncherLogger.info("Java setup: $status")
                }

                // Step 4: Loading libraries
                _state.value = LaunchState.Preparing(4, "Loading libraries", "Verifying classpaths and native binaries...")
                LauncherLogger.info("Step 4/6: Resolving classpath and native libraries...")
                val nativesDir = fileSystem.getNativesDir(versionId)
                val lwjglProfile = com.example.renderer.LwjglRuntimeProfile.resolve(versionDetail)
                val glfwStubJar = if (lwjglProfile.requiresGlfwStub) lwjglGlfwStubManager.ensureInstalled() else null
                val callbackPatchJar = if (lwjglProfile.requiresGlfwStub) lwjglGlfwStubManager.callbackPatchFile() else null
                val lwjglCheck = when (lwjglProfile.family) {
                    com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL3_NATIVE_GLFW -> {
                        val result = com.example.renderer.LwjglCompatibilityValidator.validate(versionDetail, fileSystem.librariesDir, null)
                        if (!result.valid) throw IllegalStateException("LWJGL compatibility check failed: ${result.details}")
                        result
                    }
                    com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL2_COMPAT -> {
                        val hasLegacyCompat = versionDetail.libraries.any { it.name.contains("lwjglx", ignoreCase = true) || it.name.contains("lwjgl2", ignoreCase = true) }
                        if (!hasLegacyCompat) LauncherLogger.warn("Legacy LWJGL2 profile detected without an explicit lwjglx/lwjgl2 marker; continuing with compatibility diagnostics")
                        com.example.renderer.LwjglCompatibilityValidator.Result(true, emptyList(), "Legacy LWJGL2 compatibility profile")
                    }
                }
                LauncherLogger.info("LWJGL compatibility check passed: ${lwjglCheck.details}")
                if (!nativesDir.exists() || nativesDir.listFiles()?.isEmpty() == true) {
                    LauncherLogger.warn("Natives directory is empty, unpacking libraries...")
                }

                // Step 5: Preparing renderer
                _state.value = LaunchState.Preparing(5, "Preparing renderer", "Installing Android-native GLFW/OpenGL/audio bridge (${rendererBackend.title})...")
                LauncherLogger.info("Step 5/6: Preparing Android native renderer bridge (${rendererBackend.title})...")
                val requestedNativeLwjgl = lwjglProfile.javaVersions.firstOrNull()
                    ?: if (lwjglProfile.family == com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL2_COMPAT) "2.9.4" else null
                val nativeStack = rendererManager.ensureNativeStack(requestedNativeLwjgl) { status ->
                    LauncherLogger.info("Native setup: $status")
                }
                val audioCheck = com.example.renderer.AudioCompatibilityManager.validate(
                    versionDetail, nativeStack.directory
                )
                if (!audioCheck.enabled) {
                    throw IllegalStateException("Audio compatibility check failed: ${audioCheck.reason}")
                }
                LauncherLogger.info("Audio compatibility check passed: ${audioCheck.reason}")

                val rendererDecision = com.example.renderer.RendererCompatibilityPolicy.choose(
                    rendererBackend,
                    rendererManager.gpuInfo,
                    versionDetail
                )
                if (!rendererDecision.allowed) {
                    throw IllegalStateException("Renderer is not compatible: ${rendererDecision.reason}")
                }
                val installedRendererDecision = com.example.renderer.RendererCompatibilityPolicy.validateInstalledBackend(
                    rendererDecision.effective, nativeStack, rendererManager.gpuInfo
                )
                if (!installedRendererDecision.allowed) {
                    throw IllegalStateException("Renderer backend is unavailable: ${installedRendererDecision.reason}")
                }
                val effectiveRenderer = installedRendererDecision.effective
                LauncherLogger.info("Renderer selected: ${effectiveRenderer.title} (${installedRendererDecision.reason})")
                val rendererEnv = rendererManager.buildRendererEnv(effectiveRenderer, nativesDir).toMutableMap().apply {
                    this["POJAV_NATIVEDIR"] = nativeStack.directory.absolutePath
                    this["DRIVER_PATH"] = nativeStack.directory.absolutePath
                    this["LD_LIBRARY_PATH"] = listOf(
                        nativeStack.directory.absolutePath,
                        this["LD_LIBRARY_PATH"].orEmpty()
                    ).filter { it.isNotBlank() }.joinToString(File.pathSeparator)
                    com.example.renderer.AudioCompatibilityManager.applyEnvironment(
                        this, audioCheck, nativeStack.directory
                    )
                }

                // Step 6: Starting Minecraft
                _state.value = LaunchState.Preparing(6, "Starting Minecraft", "Building command line and starting the embedded Android JVM...")
                LauncherLogger.info("Step 6/6: Building launch command...")
                val detectedRuntimeMajor = javaRuntime.versionDetails
                    .substringAfter("Java ", "")
                    .substringBefore(":")
                    .toIntOrNull()
                if (detectedRuntimeMajor == null) {
                    throw IllegalStateException("Selected Java runtime could not report a valid major version")
                }
                val javaCompatible = when (requiredJava) {
                    16 -> detectedRuntimeMajor == 17
                    else -> detectedRuntimeMajor == requiredJava
                }
                if (!javaCompatible) {
                    throw IllegalStateException(
                        "Java runtime mismatch: Minecraft requires $requiredJava but selected runtime reports $detectedRuntimeMajor"
                    )
                }
                LauncherLogger.info("Java compatibility gate passed: requested=$requiredJava runtime=$detectedRuntimeMajor")

                val launchConfig = LaunchConfig(
                    versionDetail = versionDetail,
                    username = username,
                    uuid = uuid,
                    accessToken = accessToken,
                    isOfflineAccount = isOfflineAccount,
                    ramMb = ramMb,
                    customJvmArgs = customJvmArgs,
                    javaExecutable = javaRuntime.javaExecutable,
                    serverHost = serverHost,
                    serverPort = serverPort
                )

                val nativeLwjglCheck = com.example.renderer.NativeLwjglCompatibilityManager.validate(
                    versionDetail, nativeStack.directory, lwjglProfile
                )
                if (!nativeLwjglCheck.valid) {
                    throw IllegalStateException("Native LWJGL compatibility check failed: ${nativeLwjglCheck.details}")
                }
                LauncherLogger.info("Native LWJGL ABI check passed: ${nativeLwjglCheck.details}")

                val preferLwjgl3 = lwjglProfile.apiFamily == com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL3_NATIVE_GLFW
                val selectedGlfwName = listOf("libglfw.so", "libglfw3.so").firstOrNull {
                    File(nativeStack.directory, it).isFile
                }
                val glfwLibraryName = selectedGlfwName?.removePrefix("lib")?.removeSuffix(".so") ?: "glfw"
                val launchCmd = commandBuilder.buildCommand(
                    launchConfig, rendererEnv, glfwStubJar, callbackPatchJar, listOf(nativeStack.directory), glfwLibraryName
                )
                val preflight = LaunchPreflight.verify(launchCmd, versionDetail.mainClass)
                if (!preflight.valid) {
                    throw IllegalStateException("Launch classpath preflight failed: ${preflight.errors.take(5).joinToString("; ")}")
                }
                NativeGameBridge.loadNativeStack(nativeStack.directory, preferLwjgl3 = preferLwjgl3)
                val nativeHandshake = NativeGameBridge.validateGlfwHandshake(
                    lwjglProfile.requiresGlfwStub,
                    preferLwjgl3,
                    selectedGlfwName
                )
                LauncherLogger.info("LWJGL/GLFW Java-native handshake: $nativeHandshake")
                if (!nativeHandshake.startsWith("OK:")) {
                    throw IllegalStateException("LWJGL/GLFW native handshake failed: $nativeHandshake")
                }
                LauncherLogger.info("Launch command generated, preflight and native handshake passed. Starting embedded Java runtime...")

                withContext(Dispatchers.IO) {
                    executeProcess(launchCmd, versionId, lwjglProfile.requiresGlfwStub)
                }
            } catch (e: CancellationException) {
                LauncherLogger.info("Minecraft launch sequence cancelled before embedded JVM startup.")
                _state.value = LaunchState.Idle
                throw e
            } catch (e: Exception) {
                LauncherLogger.error("Launch sequence failed: ${e.message}")
                _state.value = LaunchState.Error(e.message ?: "Unknown launch failure")
            }
        }
    }

    private suspend fun executeProcess(cmd: LaunchCommand, versionId: String, useLegacyGlfwStub: Boolean) {
        val fullCommand = mutableListOf<String>()
        fullCommand.add(cmd.executable)
        fullCommand.addAll(cmd.arguments)

        if (!NativeGameBridge.isLoaded()) {
            _state.value = LaunchState.Error("Native game bridge is unavailable; refusing to launch Minecraft without the Android Surface/JVM bridge.")
            return
        }

        val startTime = System.currentTimeMillis()
        _state.value = LaunchState.Running(startTimeMs = startTime, versionId = versionId)
        LauncherLogger.info("Waiting for Android GameSurface before starting the embedded JVM…")
        try {
            withTimeout(20_000) { surfaceReady.await() }
        } catch (e: Exception) {
            _state.value = LaunchState.Error("Minecraft surface was not created in time. Open the game screen again and retry.")
            return
        }
        LauncherLogger.info("Starting Minecraft inside the CraftDroid process through libjli/JLI_Launch… state=${NativeGameBridge.javaState()}")

        val logFile = File(fileSystem.rootDir, "logs/craftdroid-jvm.log").apply { parentFile?.mkdirs(); delete() }
        val env = cmd.environment.toMutableMap()

        // The surface can be resized/replaced between Android callbacks. Capture
        // its generation and perform EGL + GLES validation as one native transaction
        // so the JVM never starts against a different surface than the one tested.
        val surfaceGenerationBefore = NativeGameBridge.surfaceGeneration()
        val surfaceWidth = NativeGameBridge.surfaceWidth()
        val surfaceHeight = NativeGameBridge.surfaceHeight()
        if (surfaceGenerationBefore == 0L || surfaceWidth <= 0 || surfaceHeight <= 0) {
            _state.value = LaunchState.Error("Android rendering surface is unavailable or has invalid dimensions.")
            return
        }
        val graphicsPrepare = NativeGameBridge.prepareLaunchGraphics(surfaceWidth, surfaceHeight)
        LauncherLogger.info("Atomic Android graphics preparation: $graphicsPrepare")
        if (!graphicsPrepare.startsWith("OK: GRAPHICS_READY")) {
            _state.value = LaunchState.Error("Android graphics preparation failed: $graphicsPrepare")
            return
        }
        if (NativeGameBridge.surfaceGeneration() != surfaceGenerationBefore) {
            _state.value = LaunchState.Error("Android rendering surface changed during graphics preparation; launch aborted safely.")
            return
        }

        val eglStatus = NativeGameBridge.initEgl()
        LauncherLogger.info("CraftDroid EGL status: $eglStatus")
        val eglDisplay = NativeGameBridge.eglDisplayHandle()
        val eglContext = NativeGameBridge.eglContextHandle()
        val eglSurface = NativeGameBridge.eglSurfaceReadHandle()
        if (eglDisplay == 0L || eglContext == 0L || eglSurface == 0L) {
            _state.value = LaunchState.Error("Android EGL handles are unavailable after graphics preparation.")
            return
        }
        val classpathArgIndex = fullCommand.indexOf("-cp")
        if (classpathArgIndex < 0) {
            _state.value = LaunchState.Error("Launch command is missing its JVM classpath option.")
            return
        }
        if (useLegacyGlfwStub) {
            val sharedJvmProperties = listOf(
                "-Dglfwstub.initEgl=false",
                "-Dglfwstub.eglDisplay=$eglDisplay",
                "-Dglfwstub.eglContext=$eglContext",
                "-Dglfwstub.eglSurfaceRead=$eglSurface",
                "-Dglfwstub.eglSurfaceDraw=${NativeGameBridge.eglSurfaceDrawHandle()}",
                "-Dglfwstub.windowWidth=${surfaceWidth}",
                "-Dglfwstub.windowHeight=${surfaceHeight}"
            )
            fullCommand.addAll(classpathArgIndex, sharedJvmProperties)
            LauncherLogger.info("Shared Android EGL context prepared for legacy GLFW stub: display=$eglDisplay context=$eglContext surface=$eglSurface generation=$surfaceGenerationBefore")
        } else {
            LauncherLogger.info("Modern native GLFW launch: legacy glfwstub.* JVM EGL properties are not injected; Android surface bridge is provided through native/launch environment")
        }
        env["CRAFTDROID_GL_BOOTSTRAP"] = "1"
        env["CRAFTDROID_EGL_API"] = "1"
        env["CRAFTDROID_EGL_WINDOW"] = "android-native-window"
        env["CRAFTDROID_EGL_CLIENT_VERSION"] = "${if (eglStatus.contains("EGL=3")) 3 else 2}"
        env["CRAFTDROID_LOG_FILE"] = logFile.absolutePath
        env["CRAFTDROID_NATIVE_BRIDGE"] = "libcraftdroidbridge.so"
        env["CRAFTDROID_SURFACE_API"] = "1"
        env["CRAFTDROID_SURFACE_HANDLE"] = "${NativeGameBridge.surfaceHandle()}"
        env["CRAFTDROID_SURFACE_WIDTH"] = NativeGameBridge.surfaceWidth().toString()
        env["CRAFTDROID_SURFACE_HEIGHT"] = NativeGameBridge.surfaceHeight().toString()
        env["CRAFTDROID_GLFW_BRIDGE"] = "1"
        env["CRAFTDROID_GLFW_BACKEND"] = "android-surface"
        env["CRAFTDROID_GLFW_API"] = "glfw3"

        val javaHome = File(cmd.executable).parentFile?.parentFile
            ?: throw IllegalStateException("Unable to determine Java home from ${cmd.executable}")

        if (NativeGameBridge.surfaceGeneration() != surfaceGenerationBefore) {
            _state.value = LaunchState.Error("Android rendering surface changed before JVM startup; launch aborted safely.")
            return
        }
        javaLaunchActive = true
        val exitCode = try {
            coroutineScope {
                val startupMonitor = async(Dispatchers.IO) {
                    monitorMinecraftStartup(logFile)
                }
                try {
                    withContext(Dispatchers.IO) {
                        NativeGameBridge.launchJava(javaHome.absolutePath, fullCommand, env)
                    }
                } finally {
                    startupMonitor.cancel()
                    runCatching { startupMonitor.await() }
                }
            }
        } catch (e: Throwable) {
            LauncherLogger.error("Embedded JVM launch failed: ${e.message}")
            _state.value = LaunchState.Error("Embedded JVM launch failed: ${e.message}")
            return
        } finally {
            // The native launch call is synchronous. Whether it returns a
            // normal JVM exit code, an early bridge error, or throws/cancels,
            // the manager must never leave this flag stuck true. A stale
            // javaLaunchActive value makes kill() believe an embedded JVM is
            // still alive and can block future launch-state recovery.
            javaLaunchActive = false
            // A SurfaceView can be destroyed while Minecraft is running, so
            // NativeGameBridge may have deferred EGL/GLFW teardown. The native
            // JLI call is now finished and javaLaunchActive is false, therefore
            // this is the first safe point for completing that deferred cleanup
            // even when Minecraft exits naturally rather than through kill().
            NativeGameBridge.flushDeferredSurfaceClear()
        }
        
        val bridgeStateAfterLaunch = NativeGameBridge.javaState()
        LauncherLogger.info("Embedded JVM bridge state after JLI_Launch: $bridgeStateAfterLaunch")
        val durationMs = System.currentTimeMillis() - startTime
        if (exitCode < 0) {
            LauncherLogger.error("Embedded JVM bridge returned $exitCode")
            _state.value = LaunchState.Error("Android OpenJDK/JLI bridge failed (code $exitCode). Check that the selected runtime contains lib/jli/libjli.so and is an Android build.")
            return
        }
        LauncherLogger.info("Minecraft exited with code $exitCode after ${durationMs / 1000}s.")

        val capturedLog = runCatching { if (logFile.isFile) logFile.readText() else "" }.getOrDefault("")
        if (capturedLog.isNotBlank()) {
            LauncherLogger.info("Captured ${capturedLog.length} bytes of Minecraft stdout/stderr")
        }
        val diagnostics = com.example.logs.CrashDiagnostics.collect(fileSystem.rootDir, logFile)
        diagnostics.crashReport?.let { LauncherLogger.info("Minecraft crash report found: ${it.name}") }
        diagnostics.hsErr?.let { LauncherLogger.error("HotSpot fatal-error log found: ${it.name}") }
        val crashReport = diagnostics.crashReport
        val crashAnalysis = if (exitCode != 0) {
            CrashAnalyzer.analyze(exitCode, capturedLog, crashReport)
        } else null
        if (exitCode != 0) {
            val diagnosticFile = com.example.logs.CrashDiagnostics.writeSummary(fileSystem.rootDir, exitCode, diagnostics)
            if (diagnosticFile != null) {
                LauncherLogger.info("Crash diagnostics saved: ${diagnosticFile.absolutePath}")
            }
        }

        _state.value = LaunchState.Exited(
            sessionDurationMs = durationMs,
            exitCode = exitCode,
            crashAnalysis = crashAnalysis
        )
        runningProcess = null
    }


    private suspend fun monitorMinecraftStartup(logFile: File) {
        var offset = 0L
        var startedLogged = false
        var initializedLogged = false
        var frameHeartbeatLogged = false
        var menuStateLogged = false
        var inGameStateLogged = false
        var sawResourceInitialization = false
        var sawAudioInitialization = false
        var sawWorldMarker = false
        var lastObservedFrameCount = NativeGameBridge.renderFrameCount()
        var lastFrameProgressAt = System.currentTimeMillis()
        var renderWatchdogWarned = false
        val monitorStartedAt = System.currentTimeMillis()
        val deadline = monitorStartedAt + 120_000L
        while (System.currentTimeMillis() < deadline && javaLaunchActive) {
            if (logFile.isFile) {
                runCatching {
                    val length = logFile.length()
                    if (length > offset) {
                        logFile.inputStream().use { input ->
                            input.skip(offset)
                            val chunk = input.readBytes().toString(Charsets.UTF_8)
                            offset = length
                            if (chunk.isNotBlank()) {
                                val text = chunk.lowercase()
                                val renderStarted =
                                    "lwjgl version" in text ||
                                    "opengl version" in text ||
                                    "glfw" in text && "initialized" in text ||
                                    "backend library: lwjgl" in text
                                val gameInitialized =
                                    "setting user:" in text ||
                                    "openal initialized" in text ||
                                    "reloading resourcemanager" in text ||
                                    ("joining " in text && "world" in text)
                                if ("reloading resourcemanager" in text ||
                                    "resource reload" in text ||
                                    "resource manager" in text) {
                                    sawResourceInitialization = true
                                }
                                if ("sound engine started" in text ||
                                    ("openal" in text && "initialized" in text)) {
                                    sawAudioInitialization = true
                                }
                                if (listOf(
                                        "joining world", "loading world", "preparing spawn",
                                        "entering world", "respawn", "loaded <count>"
                                    ).any { marker ->
                                        if (marker == "loaded <count>") {
                                            text.contains("loaded ") && text.contains("chunk")
                                        } else text.contains(marker)
                                    }) {
                                    sawWorldMarker = true
                                }
                                if (renderStarted && !startedLogged) {
                                    startedLogged = true
                                    LauncherLogger.info("Minecraft startup detected: Java game reached LWJGL/OpenGL initialization.")
                                }
                                if (gameInitialized && !initializedLogged) {
                                    initializedLogged = true
                                    LauncherLogger.info("Minecraft initialization detected: game runtime is past renderer bootstrap.")
                                }
                            }
                        }
                    }
                }
            }
            val currentFrameCount = NativeGameBridge.renderFrameCount()
            val frameAdvanced = currentFrameCount > lastObservedFrameCount
            if (frameAdvanced) {
                lastObservedFrameCount = currentFrameCount
                lastFrameProgressAt = System.currentTimeMillis()
                if (!frameHeartbeatLogged) {
                    frameHeartbeatLogged = true
                    LauncherLogger.info("Minecraft render-loop heartbeat detected: ${currentFrameCount} successful Android-surface frame swap(s).")
                }
            }

            // Post-start watchdog: once Minecraft has produced real frames, a long
            // period with no additional successful swaps is strong evidence that the
            // render pipeline stalled. Do not kill the JVM automatically because
            // some versions legitimately pause rendering during loading or focus
            // transitions; emit targeted diagnostics instead.
            if (frameHeartbeatLogged && !renderWatchdogWarned && javaLaunchActive) {
                val noProgressMs = System.currentTimeMillis() - lastFrameProgressAt
                if (noProgressMs >= 8_000L) {
                    renderWatchdogWarned = true
                    LauncherLogger.warn(
                        "Minecraft render watchdog: no successful Android-surface frame swap for ${noProgressMs}ms. " +
                            "JVM state=${NativeGameBridge.javaState()}, surfaceGeneration=${NativeGameBridge.surfaceGeneration()}, " +
                            "frameCount=$currentFrameCount. Treating as a renderer stall diagnostic; JVM will not be killed automatically."
                    )
                }
            }

            // Clear the one-shot warning if rendering resumes after a stall.
            if (renderWatchdogWarned && frameAdvanced) {
                renderWatchdogWarned = false
            }

            // Minecraft does not expose one universal title-screen log message
            // across all versions. Infer a client-ready/menu state only after a
            // live Minecraft frame is observed together with resource/audio
            // initialization and no world-loading marker.
            if (!menuStateLogged && frameHeartbeatLogged && sawResourceInitialization &&
                sawAudioInitialization && !sawWorldMarker &&
                System.currentTimeMillis() - monitorStartedAt >= 1_500L) {
                menuStateLogged = true
                LauncherLogger.info("Minecraft game-state: MENU_READY_INFERRED (render loop + resources + audio; no world marker).")
            }

            if (!inGameStateLogged && frameHeartbeatLogged && sawWorldMarker) {
                inGameStateLogged = true
                LauncherLogger.info("Minecraft game-state: IN_GAME_DETECTED (world/loading marker + live render loop).")
            }

            kotlinx.coroutines.delay(250)
        }
        if (!frameHeartbeatLogged && javaLaunchActive) {
            LauncherLogger.warn("Minecraft startup monitor ended without observing a successful CraftDroid render-loop frame swap.")
        }
        if (!startedLogged && javaLaunchActive) {
            LauncherLogger.warn("Minecraft startup monitor timed out before an LWJGL/OpenGL initialization marker was observed.")
        }
    }

    /** Called by GameActivity when Android provides the real rendering surface. */
    @Synchronized
    fun onGameSurfaceReady(surface: Surface, width: Int, height: Int) {
        // SurfaceHolder normally emits surfaceCreated() followed immediately by
        // surfaceChanged() for the same Surface and dimensions. Treat that pair
        // as one logical surface transition; otherwise the native bridge would
        // tear down/recreate EGL + GLFW twice and invalidate launch generations.
        if (lastSurface === surface && lastSurfaceWidth == width && lastSurfaceHeight == height) {
            LauncherLogger.info("Duplicate Android surface callback ignored: ${width}x${height}")
            return
        }
        lastSurface = surface
        lastSurfaceWidth = width
        lastSurfaceHeight = height
        NativeGameBridge.setSurface(surface, width, height)
        surfaceReady.complete(Unit)
        LauncherLogger.info("Minecraft game surface attached: ${width}x${height}; native handle=${NativeGameBridge.surfaceHandle()}")
    }

    /** Called when Android destroys the rendering surface. */
    @Synchronized
    fun onGameSurfaceDestroyed() {
        lastSurface = null
        lastSurfaceWidth = 0
        lastSurfaceHeight = 0
        NativeGameBridge.clearSurface()
        LauncherLogger.info("Minecraft game surface detached (or deferred until embedded JVM stops)")
    }

    fun kill() {
        if (!stopRequestInFlight.compareAndSet(false, true)) {
            LauncherLogger.info("Ignoring duplicate Minecraft stop request; one is already in progress.")
            return
        }
        appScope.launch(Dispatchers.IO) {
            try {
                // Never report Idle while the embedded JVM is still alive. The native
                // bridge intentionally protects its GLFW/EGL resources until JLI_Launch
                // has returned, so the UI must not advertise that a new launch is safe.
                val embeddedJvmActive = javaLaunchActive || NativeGameBridge.isJavaRunning()
                if (embeddedJvmActive) {
                    LauncherLogger.info("Requesting clean shutdown of embedded Minecraft JVM… state=${NativeGameBridge.javaState()}")
                    if (!NativeGameBridge.requestJavaStop()) {
                        LauncherLogger.warn("Embedded JVM did not accept the stop request.")
                    }

                    // Give System.exit() a short grace period. This work runs on IO so
                    // Android's main/UI thread is never blocked by native JVM shutdown.
                    val deadline = System.currentTimeMillis() + 5_000L
                    while (NativeGameBridge.isJavaRunning() && System.currentTimeMillis() < deadline) {
                        try { Thread.sleep(50L) } catch (_: InterruptedException) {
                            Thread.currentThread().interrupt()
                            break
                        }
                    }
                    val stillRunning = NativeGameBridge.isJavaRunning()
                    if (stillRunning) {
                        LauncherLogger.warn(
                            "Embedded JVM is still running after stop grace period; keeping GLFW/EGL native resources alive."
                        )
                        _state.value = LaunchState.Error(
                            "Minecraft did not stop cleanly yet. The embedded JVM is still shutting down; native graphics resources remain protected until it exits."
                        )
                        return@launch
                    }

                    NativeGameBridge.shutdownGlfw()
                    NativeGameBridge.flushDeferredSurfaceClear()
                } else {
                    // No embedded VM exists yet. Cancelling the preparation coroutine is
                    // safe and prevents an Abort button from being overwritten by a late
                    // launch callback.
                    launchJob?.cancel()
                    NativeGameBridge.shutdownGlfw()
                    NativeGameBridge.flushDeferredSurfaceClear()
                }

                runningProcess?.destroy()
                runningProcess = null
                if (!NativeGameBridge.isJavaRunning()) {
                    _state.value = LaunchState.Idle
                    LauncherLogger.info("Minecraft process stopped by user.")
                } else {
                    LauncherLogger.warn("Minecraft stop request timed out; keeping launcher in a protected state until the embedded JVM exits.")
                }
            } catch (e: Exception) {
                LauncherLogger.warn("Error stopping process: ${e.message}")
            } finally {
                stopRequestInFlight.set(false)
            }
        }
    }

    fun resetToHome() {
        if (javaLaunchActive || NativeGameBridge.isJavaRunning()) {
            LauncherLogger.warn("Ignoring reset-to-home while embedded Minecraft JVM is active.")
            return
        }
        launchJob?.cancel()
        _state.value = LaunchState.Idle
    }
}
