package com.example.minecraft

import android.util.Log
import com.example.filesystem.MinecraftFileSystem
import com.example.versions.VersionDetail
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.util.zip.ZipFile

/**
 * Step 22: lightweight pre-launch mod discovery and compatibility checks.
 *
 * This deliberately does not execute mod code. It only reads common metadata
 * files from each mod JAR and checks obvious Minecraft/loader mismatches.
 */
data class ModCompatibilityResult(
    val valid: Boolean,
    val loader: String,
    val scanned: Int,
    val enabled: Int,
    val errors: List<String>,
    val warnings: List<String>
)

data class DiscoveredMod(
    val file: File,
    val modId: String?,
    val name: String,
    val loader: String,
    val minecraftVersions: Set<String>,
    val dependencies: Set<String>
)

class ModCompatibilityManager(private val fileSystem: MinecraftFileSystem) {

    suspend fun validate(version: VersionDetail): ModCompatibilityResult = withContext(Dispatchers.IO) {
        val loader = detectLoader(version)
        val files = fileSystem.modsDir.listFiles()
            ?.filter { it.isFile && it.name.endsWith(".jar", ignoreCase = true) }
            ?.sortedBy { it.name.lowercase() }
            .orEmpty()

        val errors = mutableListOf<String>()
        val warnings = mutableListOf<String>()
        var enabled = 0
        val discovered = mutableListOf<DiscoveredMod>()

        if (files.isEmpty()) {
            return@withContext ModCompatibilityResult(true, loader, 0, 0, emptyList(), emptyList())
        }

        for (file in files) {
            enabled++
            try {
                val mod = readMetadata(file, loader)
                discovered += mod

                if (loader == "vanilla") {
                    warnings += "${file.name}: mods are present but Minecraft version ${version.id} has no Fabric/Forge/NeoForge loader detected."
                    continue
                }

                if (mod.loader != "unknown" && mod.loader != loader) {
                    errors += "${file.name}: detected ${mod.loader} mod, but selected profile uses $loader."
                }

                if (mod.minecraftVersions.isNotEmpty() && !matchesMinecraftVersion(version.id, mod.minecraftVersions)) {
                    errors += "${file.name}: metadata targets ${mod.minecraftVersions.joinToString(", ")}, not Minecraft ${version.id}."
                }
            } catch (e: Exception) {
                warnings += "${file.name}: could not read mod metadata (${e.message ?: "unknown error"})."
            }
        }

        // Duplicate IDs are a common source of confusing loader failures.
        discovered.filter { it.modId != null }
            .groupBy { it.modId }
            .filterValues { it.size > 1 }
            .forEach { (id, mods) ->
                warnings += "Duplicate mod id '$id': ${mods.joinToString { it.file.name }}"
            }

        val result = ModCompatibilityResult(
            valid = errors.isEmpty(),
            loader = loader,
            scanned = files.size,
            enabled = enabled,
            errors = errors,
            warnings = warnings
        )
        Log.i(TAG, "Mod scan: loader=$loader scanned=${files.size} valid=${result.valid}")
        result
    }

    fun detectLoader(version: VersionDetail): String {
        val text = buildString {
            append(version.id).append('\n')
            append(version.mainClass).append('\n')
            version.libraries.forEach { append(it.name).append('\n') }
        }.lowercase()
        return when {
            "neoforge" in text || "net.neoforged" in text -> "neoforge"
            "forge" in text || "net.minecraftforge" in text || "fmlclientlaunchprovider" in text -> "forge"
            "fabric" in text || "net.fabricmc" in text -> "fabric"
            else -> "vanilla"
        }
    }

    private fun readMetadata(file: File, expectedLoader: String): DiscoveredMod {
        ZipFile(file).use { zip ->
            val fabric = zip.getEntry("fabric.mod.json")
            if (fabric != null) {
                val json = JSONObject(zip.getInputStream(fabric).bufferedReader().use { it.readText() })
                return DiscoveredMod(
                    file = file,
                    modId = json.optString("id").takeIf { it.isNotBlank() },
                    name = json.optString("name", file.nameWithoutExtension),
                    loader = "fabric",
                    minecraftVersions = extractFabricMinecraftVersions(json),
                    dependencies = extractFabricDependencies(json)
                )
            }

            val modsToml = zip.getEntry("META-INF/mods.toml")
            if (modsToml != null) {
                val text = zip.getInputStream(modsToml).bufferedReader().use { it.readText() }
                val modId = Regex("modId\\s*=\\s*\\\"([^\\\"]+)\\\"").find(text)?.groupValues?.getOrNull(1)
                val display = Regex("displayName\\s*=\\s*\\\"([^\\\"]+)\\\"").find(text)?.groupValues?.getOrNull(1)
                val versions = Regex("(?:versionRange|loaderVersion|minecraftVersionRange)\\s*=\\s*\\\"([^\\\"]+)\\\"")
                    .findAll(text).map { it.groupValues[1] }.toSet()
                return DiscoveredMod(file, modId, display ?: file.nameWithoutExtension, if (expectedLoader == "neoforge") "neoforge" else "forge", versions, emptySet())
            }

            val legacy = zip.getEntry("mcmod.info")
            if (legacy != null) {
                val text = zip.getInputStream(legacy).bufferedReader().use { it.readText() }
                val json = JSONArray("[$text]").optJSONObject(0)
                val obj = json ?: runCatching { JSONObject(text) }.getOrNull()
                val first = if (obj?.has("modList") == true) obj.optJSONArray("modList")?.optJSONObject(0) else obj
                return DiscoveredMod(file, first?.optString("modid")?.takeIf { it.isNotBlank() }, first?.optString("name") ?: file.nameWithoutExtension, "forge", emptySet(), emptySet())
            }
        }
        return DiscoveredMod(file, null, file.nameWithoutExtension, "unknown", emptySet(), emptySet())
    }

    private fun extractFabricMinecraftVersions(json: JSONObject): Set<String> {
        val out = mutableSetOf<String>()
        val depends = json.optJSONObject("depends") ?: return out
        val minecraft = depends.opt("minecraft")
        if (minecraft is String) out += minecraft
        return out
    }

    private fun extractFabricDependencies(json: JSONObject): Set<String> {
        val out = mutableSetOf<String>()
        val depends = json.optJSONObject("depends") ?: return out
        depends.keys().forEach { if (it != "minecraft") out += it }
        return out
    }

    private fun matchesMinecraftVersion(version: String, declarations: Set<String>): Boolean {
        if (declarations.isEmpty()) return true
        return declarations.any { declaration ->
            val d = declaration.trim()
            d == version || d == "*" || d.contains(version) || version.contains(d.removePrefix("="))
        }
    }

    companion object {
        private const val TAG = "CraftDroid-Mods"
    }
}
