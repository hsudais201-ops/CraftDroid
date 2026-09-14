package com.example.launcher

import android.content.Context
import org.json.JSONObject
import java.io.File

/** Builds a deterministic, filesystem-backed launch handoff for one installed Minecraft version. */
object MinecraftLaunchCommandBuilder {
    data class Result(
        val version: String,
        val mainClass: String,
        val classpath: List<File>,
        val nativeDir: File,
        val assetIndex: String?,
        val valid: Boolean,
        val error: String? = null
    ) {
        val classpathString: String get() = classpath.joinToString(File.pathSeparator) { it.absolutePath }
    }

    fun build(context: Context, version: String): Result {
        val paths = MinecraftLaunchPaths.resolve(context, version)
        if (!paths.valid) return Result(version, "", emptyList(), paths.nativesDir, null, false, paths.error)
        return try {
            val metadata = JSONObject(File(paths.versionDir, "$version.json").readText(Charsets.UTF_8))
            val mainClass = metadata.optString("mainClass").trim()
            if (mainClass.isBlank()) return Result(version, "", emptyList(), paths.nativesDir, null, false, "Minecraft main class is missing")

            val classpath = mutableListOf<File>()
            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    if (!libraryAllowed(library)) continue
                    val artifact = library.optJSONObject("downloads")?.optJSONObject("artifact") ?: continue
                    val path = artifact.optString("path")
                    if (path.isNotBlank()) {
                        val file = File(paths.librariesDir, path)
                        if (file.isFile && file.length() > 0L) classpath += file
                    }
                }
            }
            classpath += paths.clientJar
            val assetIndex = metadata.optJSONObject("assetIndex")?.optString("id")?.takeIf { it.isNotBlank() }
            Result(version, mainClass, classpath.distinctBy { it.absolutePath }, paths.nativesDir, assetIndex, true)
        } catch (t: Throwable) {
            Result(version, "", emptyList(), paths.nativesDir, null, false, t.message ?: t.javaClass.simpleName)
        }
    }

    private fun libraryAllowed(library: JSONObject): Boolean {
        val rules = library.optJSONArray("rules") ?: return true
        var allowed = false
        for (i in 0 until rules.length()) {
            val rule = rules.optJSONObject(i) ?: continue
            val action = rule.optString("action", "allow").equals("allow", ignoreCase = true)
            val os = rule.optJSONObject("os")
            val osName = os?.optString("name")?.trim().orEmpty()
            val arch = os?.optString("arch")?.trim().orEmpty()
            val osMatches = osName.isBlank() || osName.equals("linux", ignoreCase = true)
            val currentArch = System.getProperty("os.arch", "").lowercase()
            val archMatches = arch.isBlank() || currentArch.contains(arch.lowercase())
            if (osMatches && archMatches) allowed = action
        }
        return allowed
    }
}
