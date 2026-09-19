package com.example.input

import android.content.Context
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ControlLayoutStorage(private val context: Context) {

    private val storageFile: File
        get() = File(context.filesDir, "control_profiles.json")

    private val activeProfileFile: File
        get() = File(context.filesDir, "active_profile_id.txt")

    suspend fun loadAllProfiles(): List<ControlProfile> = withContext(Dispatchers.IO) {
        val list = mutableListOf<ControlProfile>()
        if (storageFile.exists()) {
            try {
                val content = storageFile.readText()
                val root = JSONObject(content)
                val array = root.optJSONArray("profiles") ?: JSONArray()
                for (i in 0 until array.length()) {
                    val pJson = array.optJSONObject(i) ?: continue
                    try {
                        list.add(ControlProfile.fromJson(pJson))
                    } catch (e: Exception) {
                        LauncherLogger.warn("Failed to parse profile item: ${e.message}")
                    }
                }
            } catch (e: Exception) {
                LauncherLogger.error("Failed to read control profiles file: ${e.message}")
            }
        }

        // Ensure all built-in profiles are present if not loaded
        val builtins = listOf(
            ControlProfile.createDefaultProfile(),
            ControlProfile.createPvpProfile(),
            ControlProfile.createSurvivalProfile(),
            ControlProfile.createBuildingProfile(),
            ControlProfile.createTabletProfile(),
            ControlProfile.createControllerProfile()
        )

        val existingIds = list.map { it.id }.toSet()
        val merged = list.toMutableList()
        for (builtin in builtins) {
            if (!existingIds.contains(builtin.id)) {
                merged.add(builtin)
            }
        }

        if (merged.isEmpty()) {
            merged.add(ControlProfile.createDefaultProfile())
        }

        merged
    }

    suspend fun saveState(profiles: List<ControlProfile>, activeProfileId: String) = withContext(Dispatchers.IO) {
        try {
            val root = JSONObject().apply {
                val array = JSONArray()
                profiles.forEach { array.put(it.toJson()) }
                put("profiles", array)
                put("version", 3)
                put("activeProfileId", activeProfileId)
            }
            val tmp = File(context.filesDir, "control_profiles.json.tmp")
            tmp.writeText(root.toString(2))
            if (!tmp.renameTo(storageFile)) {
                storageFile.writeText(root.toString(2))
                tmp.delete()
            }
            activeProfileFile.writeText(activeProfileId)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to atomically save control state: ${e.message}")
        }
    }

    suspend fun saveAllProfiles(profiles: List<ControlProfile>) = withContext(Dispatchers.IO) {
        try {
            val root = JSONObject()
            val array = JSONArray()
            profiles.forEach { array.put(it.toJson()) }
            root.put("profiles", array)
            root.put("version", 2)
            storageFile.writeText(root.toString(2))
        } catch (e: Exception) {
            LauncherLogger.error("Failed to save control profiles: ${e.message}")
        }
    }

    suspend fun getActiveProfileId(): String = withContext(Dispatchers.IO) {
        if (activeProfileFile.exists()) {
            activeProfileFile.readText().trim()
        } else if (storageFile.exists()) {
            runCatching { JSONObject(storageFile.readText()).optString("activeProfileId", "default") }
                .onFailure { LauncherLogger.warn("Failed to read active control profile id: " + it.message) }
                .getOrDefault("default")
        } else {
            "default"
        }
    }

    suspend fun setActiveProfileId(id: String) = withContext(Dispatchers.IO) {
        try {
            activeProfileFile.writeText(id)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to save active profile id: ${e.message}")
        }
    }

    /**
     * Validates and imports a JSON string representation of a profile.
     * Throws IllegalArgumentException on invalid schema to prevent corrupted data.
     */
    fun validateAndImportProfile(jsonStr: String): ControlProfile {
        val root = JSONObject(jsonStr)
        val name = root.optString("name", "").trim()
        require(name.isNotBlank()) { "Profile must have a valid name." }

        // Sanitize name
        val sanitizedName = name.take(30).replace(Regex("[^a-zA-Z0-9 _-]"), "")
        require(sanitizedName.isNotBlank()) { "Profile name contains invalid characters." }

        val profile = ControlProfile.fromJson(root)
        // Ensure imported profile is marked as custom with a unique ID
        return profile.copy(
            id = "imported_${System.currentTimeMillis()}_${java.util.UUID.randomUUID().toString().take(4)}",
            name = sanitizedName,
            isCustom = true
        )
    }

    fun exportProfileToJson(profile: ControlProfile): String {
        return profile.toJson().toString(2)
    }
}
