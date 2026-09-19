package com.example.launcher

import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.versions.LibraryRule
import com.example.versions.VersionDetail
import com.example.versions.VersionJsonParser
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

data class LaunchConfig(
    val versionDetail: VersionDetail,
    val username: String,
    val uuid: String,
    val accessToken: String,
    val isOfflineAccount: Boolean = false,
    val ramMb: Int = 2048,
    val minRamMb: Int = 512,
    val customJvmArgs: String = "",
    val resolutionWidth: Int = 1920,
    val resolutionHeight: Int = 1080,
    val javaExecutable: File,
    val serverHost: String? = null,
    val serverPort: Int? = null
)

data class LaunchCommand(
    val executable: String,
    val arguments: List<String>,
    val workingDir: File,
    val environment: Map<String, String>,
    val classpathString: String
)

class LaunchCommandBuilder(
    private val fileSystem: MinecraftFileSystem,
    private val versionParser: VersionJsonParser
) {

    fun buildCommand(config: LaunchConfig, extraEnv: Map<String, String> = emptyMap(), glfwStubJar: File? = null, callbackPatchJar: File? = null, extraNativeDirs: List<File> = emptyList(), glfwLibraryName: String = "glfw"): LaunchCommand {
        val args = mutableListOf<String>()

        // 1. JVM Memory Arguments
        args.add("-Xms${config.minRamMb}M")
        args.add("-Xmx${config.ramMb}M")

        // 2. Android native library path.
        // Minecraft's extracted native archives contain desktop Linux .so files.
        // Do NOT expose that directory through java.library.path/org.lwjgl.librarypath
        // on Android: a desktop library can win the lookup and fail with missing
        // glibc/libpthread symbols or an ABI mismatch. The Android/Pojav-compatible
        // native stack is supplied through extraNativeDirs instead.
        val nativesDir = fileSystem.getNativesDir(config.versionDetail.id)
        val nativeSearchPath = extraNativeDirs.filter { it.isDirectory }.distinctBy { it.absolutePath }.joinToString(File.pathSeparator) { it.absolutePath }
        args.add("-Djava.library.path=$nativeSearchPath")
        args.add("-Dorg.lwjgl.librarypath=$nativeSearchPath")

        // 3. Minecraft Launcher Brand properties
        args.add("-Dminecraft.launcher.brand=minecraft-launcher")
        args.add("-Dminecraft.launcher.version=2.1")
        args.add("-Djava.awt.headless=false")
        args.add("-Djava.home=${config.javaExecutable.parentFile?.parentFile?.absolutePath.orEmpty()}")
        args.add("-Djava.io.tmpdir=${File(fileSystem.rootDir, "tmp").absolutePath}")
        args.add("-Dminecraft.client.jar=${fileSystem.getVersionJarFile(config.versionDetail.id).absolutePath}")
        args.add("-Dorg.lwjgl.opengl.Display.allowSoftwareOpenGL=true")
        args.add("-Dorg.lwjgl.system.allocator=system")
        val normalizedGlfwName = glfwLibraryName.removePrefix("lib").removeSuffix(".so")
        val lwjglGlfwName = if (normalizedGlfwName == "glfw3") "glfw3" else "glfw"
        args.add("-Dorg.lwjgl.glfw.libname=$lwjglGlfwName")
        args.add("-Dorg.lwjgl.util.NoChecks=true")
        if (glfwStubJar?.isFile == true) {
            args.add("-Dglfwstub.windowWidth=${config.resolutionWidth}")
            args.add("-Dglfwstub.windowHeight=${config.resolutionHeight}")
            args.add("-Dglfwstub.initEgl=false")
        }
        args.add("-Djdk.lang.Process.launchMechanism=FORK")
        args.add("-Dlog4j2.formatMsgNoLookups=true")
        // Mojang version manifests may provide a client logging configuration.
        // Resolve it from the normal assets/log_configs directory instead of
        // hard-coding a particular Minecraft version.
        config.versionDetail.logging?.let { logging ->
            val logFile = File(fileSystem.assetsDir, "log_configs/${logging.clientFilePath}")
            if (logFile.isFile) {
                args.add("-Dlog4j.configurationFile=${logFile.absolutePath}")
                LauncherLogger.info("Using Minecraft client logging config: ${logFile.absolutePath}")
            } else {
                LauncherLogger.warn("Minecraft logging config is missing: ${logFile.absolutePath}")
            }
        }
        if (glfwStubJar?.isFile == true) {
            args.add("-Dglfwstub.debugInput=false")
        }

        // 4. Custom user JVM arguments (validated against shell-injection)
        if (config.customJvmArgs.isNotBlank()) {
            val tokens = config.customJvmArgs.trim().split(Regex("\\s+"))
            for (token in tokens) {
                if (isValidJvmArg(token)) {
                    args.add(token)
                } else {
                    LauncherLogger.warn("Ignored suspicious custom JVM argument: $token")
                }
            }
        }

        // 5. Version-defined JVM arguments from JSON (modern Minecraft)
        val templateMap = buildTemplateMap(config)
        for (item in config.versionDetail.jvmArguments) {
            val resolved = resolveArgumentItem(item, templateMap)
            args.addAll(resolved)
        }

        // 6. Build Classpath
        val classpathEntries = mutableListOf<String>()
        if (glfwStubJar?.isFile == true) {
            callbackPatchJar?.takeIf { it.isFile }?.let { classpathEntries.add(it.absolutePath) }
            classpathEntries.add(glfwStubJar.absolutePath)
        }

        // Resolve every Mojang artifact deterministically. Missing/corrupt JARs
        // must be repaired before this point; silently omitting them produces
        // misleading ClassNotFoundException/NoClassDefFoundError failures later.
        val resolvedClasspath = LaunchClasspathResolver.resolve(
            config.versionDetail,
            fileSystem.librariesDir,
            fileSystem.getVersionJarFile(config.versionDetail.id)
        )
        if (!resolvedClasspath.valid) {
            throw IllegalStateException(
                "Resolved Minecraft classpath is incomplete: " +
                    "missing=${resolvedClasspath.missing.size}, corrupt=${resolvedClasspath.corrupt.size}"
            )
        }
        classpathEntries += resolvedClasspath.entries.map { it.absolutePath }
        val classpathString = classpathEntries.distinct().joinToString(File.pathSeparator)

        args.add("-cp")
        args.add(classpathString)

        // 7. Main Class
        args.add(config.versionDetail.mainClass)

        // 8. Game Arguments
        if (config.versionDetail.legacyMinecraftArguments != null) {
            // Legacy Minecraft Arguments (e.g. 1.12.2 and older)
            val legacyTokens = config.versionDetail.legacyMinecraftArguments.split(" ")
            for (token in legacyTokens) {
                args.add(substituteTemplate(token, templateMap))
            }
        } else if (config.versionDetail.gameArguments.isNotEmpty()) {
            // Modern Game Arguments array
            for (item in config.versionDetail.gameArguments) {
                val resolved = resolveArgumentItem(item, templateMap)
                args.addAll(resolved)
            }
        } else {
            // Standard fallback game arguments
            args.addAll(listOf(
                "--username", config.username,
                "--version", config.versionDetail.id,
                "--gameDir", fileSystem.rootDir.absolutePath,
                "--assetsDir", fileSystem.assetsDir.absolutePath,
                "--assetIndex", config.versionDetail.assetIndex.id,
                "--uuid", config.uuid,
                "--accessToken", config.accessToken,
                "--userType", if (config.isOfflineAccount) "legacy" else "msa",
                "--versionType", "release"
            ))
        }

        if (!config.serverHost.isNullOrBlank() && config.serverPort != null &&
            args.none { it == "--server" }
        ) {
            args.add("--server")
            args.add(config.serverHost)
            args.add("--port")
            args.add(config.serverPort.toString())
        }

        val javaHome = config.javaExecutable.parentFile?.parentFile
        val environment = LinkedHashMap<String, String>()
        environment.putAll(extraEnv)
        environment["JAVA_HOME"] = javaHome?.absolutePath ?: ""
        environment["HOME"] = fileSystem.rootDir.absolutePath
        environment["TMPDIR"] = File(fileSystem.rootDir, "tmp").apply { mkdirs() }.absolutePath
        environment["POJAV_NATIVEDIR"] = extraNativeDirs.firstOrNull { it.isDirectory }?.absolutePath ?: nativesDir.absolutePath
        environment["CRAFTDROID_NATIVE_LIBRARY_PATH"] = nativeSearchPath
        environment["AWTSTUB_WIDTH"] = config.resolutionWidth.toString()
        environment["AWTSTUB_HEIGHT"] = config.resolutionHeight.toString()

        val runtimeBin = javaHome?.let { File(it, "bin").absolutePath }
        val currentPath = System.getenv("PATH").orEmpty()
        environment["PATH"] = listOfNotNull(runtimeBin, currentPath.takeIf { it.isNotBlank() })
            .joinToString(File.pathSeparator)

        val currentLd = System.getenv("LD_LIBRARY_PATH").orEmpty()
        // Android OpenJDK has VM libraries in architecture-specific directories.
        // Put the JLI/VM directories first so libjli can resolve libjvm and its
        // companions before Minecraft/native renderer libraries with the same
        // generic names are considered.
        val runtimeLdDirs = listOf(
            javaHome?.let { File(it, "lib/jli") },
            javaHome?.let { File(it, "lib/server") },
            javaHome?.let { File(it, "lib/client") },
            javaHome?.let { File(it, "lib") },
            javaHome?.let { File(it, "lib/aarch64/jli") },
            javaHome?.let { File(it, "lib/aarch64") },
            javaHome?.let { File(it, "lib/arm/jli") },
            javaHome?.let { File(it, "lib/arm") },
            javaHome?.let { File(it, "lib/aarch32/jli") },
            javaHome?.let { File(it, "lib/aarch32") },
            javaHome?.let { File(it, "lib/x86_64/jli") },
            javaHome?.let { File(it, "lib/x86_64") },
            javaHome?.let { File(it, "lib/i386/jli") },
            javaHome?.let { File(it, "lib/i386") }
        ).filterNotNull().filter { it.isDirectory }.map { it.absolutePath }
        val nativeLdDirs = extraNativeDirs.filter { it.isDirectory }.distinctBy { it.absolutePath }.map { it.absolutePath }
        environment["LD_LIBRARY_PATH"] = (runtimeLdDirs + nativeLdDirs + listOfNotNull(
            extraEnv["LD_LIBRARY_PATH"],
            currentLd.takeIf { it.isNotBlank() }
        )).distinct().joinToString(File.pathSeparator)

        return LaunchCommand(
            executable = config.javaExecutable.absolutePath,
            arguments = args,
            workingDir = fileSystem.rootDir,
            environment = environment,
            classpathString = classpathString
        )
    }

    private fun buildTemplateMap(config: LaunchConfig): Map<String, String> {
        val map = HashMap<String, String>()
        map["auth_player_name"] = config.username
        map["version_name"] = config.versionDetail.id
        map["game_directory"] = fileSystem.rootDir.absolutePath
        map["assets_root"] = fileSystem.assetsDir.absolutePath
        map["game_assets"] = fileSystem.assetsDir.absolutePath
        map["assets_index_name"] = config.versionDetail.assetIndex.id
        map["assets"] = config.versionDetail.assets ?: config.versionDetail.assetIndex.id
        map["auth_uuid"] = config.uuid
        map["auth_access_token"] = config.accessToken
        map["clientid"] = "00000000402b5328"
        map["auth_xuid"] = if (config.isOfflineAccount) "" else config.uuid
        map["user_type"] = if (config.isOfflineAccount) "legacy" else "msa"
        map["user_properties"] = "{}"
        map["version_type"] = "release"
        map["resolution_width"] = config.resolutionWidth.toString()
        map["resolution_height"] = config.resolutionHeight.toString()
        map["natives_directory"] = fileSystem.getNativesDir(config.versionDetail.id).absolutePath
        map["launcher_name"] = "minecraft-launcher"
        map["launcher_version"] = "2.1"
        map["classpath"] = "\${classpath}" // handled via -cp
        return map
    }

    private fun resolveArgumentItem(item: Any, templateMap: Map<String, String>): List<String> {
        val result = mutableListOf<String>()
        when (item) {
            is String -> {
                // If contains template like ${auth_player_name}
                if (!item.contains("\${classpath}")) {
                    result.add(substituteTemplate(item, templateMap))
                }
            }
            is JSONObject -> {
                // Rule-based argument
                val rulesArray = item.optJSONArray("rules")
                val rules = mutableListOf<LibraryRule>()
                if (rulesArray != null) {
                    for (i in 0 until rulesArray.length()) {
                        val r = rulesArray.getJSONObject(i)
                        val os = r.optJSONObject("os")
                        rules.add(
                            LibraryRule(
                                action = r.getString("action"),
                                osName = os?.optString("name"),
                                osVersion = os?.optString("version"),
                                osArch = os?.optString("arch")
                            )
                        )
                    }
                }

                if (versionParser.evaluateRules(rules)) {
                    val value = item.opt("value")
                    when (value) {
                        is String -> result.add(substituteTemplate(value, templateMap))
                        is JSONArray -> {
                            for (j in 0 until value.length()) {
                                val v = value.getString(j)
                                if (!v.contains("\${classpath}")) {
                                    result.add(substituteTemplate(v, templateMap))
                                }
                            }
                        }
                    }
                }
            }
        }
        return result
    }

    private fun substituteTemplate(template: String, values: Map<String, String>): String {
        var str = template
        for ((key, value) in values) {
            str = str.replace("\${$key}", value)
        }
        return str
    }

    private fun isValidJvmArg(arg: String): Boolean {
        // Prevent command injection, piping, or arbitrary shell execution
        return !arg.contains(";") &&
               !arg.contains("&") &&
               !arg.contains("|") &&
               !arg.contains(">") &&
               !arg.contains("<") &&
               !arg.contains("`") &&
               !arg.contains("$(") &&
               (arg.startsWith("-") || arg.startsWith("+"))
    }
}
