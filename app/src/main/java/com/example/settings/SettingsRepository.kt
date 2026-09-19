package com.example.settings

import android.app.ActivityManager
import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.example.renderer.RendererBackend
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "launcher_settings")

data class LauncherSettings(
    val selectedVersionId: String = "1.21.4",
    val ramMb: Int = 2048,
    val renderer: RendererBackend = RendererBackend.AUTO,
    val customJvmArgs: String = "",
    val javaRuntimeOverride: Int? = null,
    val fullScreen: Boolean = true,
    val maxFps: Int = 60,
    val touchOpacity: Float = 0.75f,
    val touchScale: Float = 1.0f,
    val mouseSensitivity: Float = 1.0f,
    val invertY: Boolean = false,
    val virtualMouseEnabled: Boolean = false,
    val showSnapshots: Boolean = false,
    val customButtonLayout: String = "",
    val enableLocalTestProfiles: Boolean = true
)

class SettingsRepository(private val context: Context) {

    private object Keys {
        val SELECTED_VERSION = stringPreferencesKey("selected_version")
        val RAM_MB = intPreferencesKey("ram_mb")
        val RENDERER = stringPreferencesKey("renderer_backend")
        val JVM_ARGS = stringPreferencesKey("jvm_args")
        val JAVA_RUNTIME = intPreferencesKey("java_runtime_override")
        val FULLSCREEN = booleanPreferencesKey("fullscreen")
        val MAX_FPS = intPreferencesKey("max_fps")
        val TOUCH_OPACITY = floatPreferencesKey("touch_opacity")
        val TOUCH_SCALE = floatPreferencesKey("touch_scale")
        val MOUSE_SENS = floatPreferencesKey("mouse_sens")
        val INVERT_Y = booleanPreferencesKey("invert_y")
        val VIRTUAL_MOUSE = booleanPreferencesKey("virtual_mouse")
        val SHOW_SNAPSHOTS = booleanPreferencesKey("show_snapshots")
        val CUSTOM_LAYOUT = stringPreferencesKey("custom_button_layout")
        val ENABLE_LOCAL_TEST_PROFILES = booleanPreferencesKey("enable_local_test_profiles")
    }

    val settingsFlow: Flow<LauncherSettings> = context.dataStore.data.map { prefs ->
        LauncherSettings(
            selectedVersionId = prefs[Keys.SELECTED_VERSION] ?: "1.21.4",
            ramMb = prefs[Keys.RAM_MB] ?: 2048,
            renderer = try {
                RendererBackend.valueOf(prefs[Keys.RENDERER] ?: RendererBackend.AUTO.name)
            } catch (_: Exception) {
                RendererBackend.AUTO
            },
            customJvmArgs = prefs[Keys.JVM_ARGS] ?: "",
            javaRuntimeOverride = prefs[Keys.JAVA_RUNTIME],
            fullScreen = prefs[Keys.FULLSCREEN] ?: true,
            maxFps = prefs[Keys.MAX_FPS] ?: 60,
            touchOpacity = prefs[Keys.TOUCH_OPACITY] ?: 0.75f,
            touchScale = prefs[Keys.TOUCH_SCALE] ?: 1.0f,
            mouseSensitivity = prefs[Keys.MOUSE_SENS] ?: 1.0f,
            invertY = prefs[Keys.INVERT_Y] ?: false,
            virtualMouseEnabled = prefs[Keys.VIRTUAL_MOUSE] ?: false,
            showSnapshots = prefs[Keys.SHOW_SNAPSHOTS] ?: false,
            customButtonLayout = prefs[Keys.CUSTOM_LAYOUT] ?: "",
            enableLocalTestProfiles = prefs[Keys.ENABLE_LOCAL_TEST_PROFILES] ?: true
        )
    }

    fun getDeviceTotalRamMb(): Int {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
        val memoryInfo = ActivityManager.MemoryInfo()
        return if (am != null) {
            am.getMemoryInfo(memoryInfo)
            (memoryInfo.totalMem / (1024 * 1024)).toInt()
        } else {
            4096
        }
    }

    fun getDeviceAvailableRamMb(): Int {
        val am = context.getSystemService(Context.ACTIVITY_SERVICE) as? ActivityManager
        val memoryInfo = ActivityManager.MemoryInfo()
        return if (am != null) {
            am.getMemoryInfo(memoryInfo)
            (memoryInfo.availMem / (1024 * 1024)).toInt()
        } else {
            2048
        }
    }

    suspend fun updateSelectedVersion(versionId: String) {
        context.dataStore.edit { it[Keys.SELECTED_VERSION] = versionId }
    }

    suspend fun updateRam(ramMb: Int) {
        context.dataStore.edit { it[Keys.RAM_MB] = ramMb }
    }

    suspend fun updateRenderer(backend: RendererBackend) {
        context.dataStore.edit { it[Keys.RENDERER] = backend.name }
    }

    suspend fun updateJvmArgs(args: String) {
        context.dataStore.edit { it[Keys.JVM_ARGS] = args }
    }

    suspend fun updateJavaRuntimeOverride(major: Int?) {
        context.dataStore.edit {
            if (major == null) it.remove(Keys.JAVA_RUNTIME)
            else it[Keys.JAVA_RUNTIME] = major
        }
    }

    fun safeMemoryPlan(requestedMb: Int): Pair<Int, Int> {
        val availableMb = getDeviceAvailableRamMb().coerceAtLeast(512)
        val cap = (availableMb * 0.55f).toInt().coerceAtLeast(768).coerceAtMost(4096)
        val maxRam = requestedMb.coerceIn(768, cap)
        val minRam = (maxRam / 4).coerceIn(256, 768)
        return maxRam to minRam
    }

    suspend fun updateControls(opacity: Float, scale: Float, sens: Float, invertY: Boolean, virtualMouse: Boolean) {
        context.dataStore.edit {
            it[Keys.TOUCH_OPACITY] = opacity
            it[Keys.TOUCH_SCALE] = scale
            it[Keys.MOUSE_SENS] = sens
            it[Keys.INVERT_Y] = invertY
            it[Keys.VIRTUAL_MOUSE] = virtualMouse
        }
    }

    suspend fun updateShowSnapshots(show: Boolean) {
        context.dataStore.edit { it[Keys.SHOW_SNAPSHOTS] = show }
    }

    suspend fun updateCustomButtonLayout(layout: String) {
        context.dataStore.edit { it[Keys.CUSTOM_LAYOUT] = layout }
    }

    suspend fun updateEnableLocalTestProfiles(enabled: Boolean) {
        context.dataStore.edit { it[Keys.ENABLE_LOCAL_TEST_PROFILES] = enabled }
    }
}
