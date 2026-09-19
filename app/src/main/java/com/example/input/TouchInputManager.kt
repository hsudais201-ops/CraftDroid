package com.example.input

import android.content.Context
import com.example.logs.LauncherLogger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * TouchInputManager manages completely separated, independently configurable touch controls,
 * multiple profiles, multi-touch tracking, and routing to the Minecraft input bridge.
 */
class TouchInputManager(
    private val context: Context? = null,
    private val scope: CoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
) {
    val inputBridge = InputBridge()
    val inputMapper = InputMapper(inputBridge)
    private val storage = context?.let { ControlLayoutStorage(it) }
    @Volatile private var saveJob: Job? = null
    private val saveLock = Any()

    // Multi-touch tracking: pointerId -> controlId
    private val pointerToControlMap = ConcurrentHashMap<Int, String>()
    private val nextPointerToken = AtomicInteger(1)
    // Set of pressed control IDs
    private val _pressedControlIds = MutableStateFlow<Set<String>>(emptySet())
    val pressedControlIds: StateFlow<Set<String>> = _pressedControlIds.asStateFlow()

    // Profiles state
    private val _allProfiles = MutableStateFlow<List<ControlProfile>>(
        listOf(
            ControlProfile.createDefaultProfile(),
            ControlProfile.createPvpProfile(),
            ControlProfile.createSurvivalProfile(),
            ControlProfile.createBuildingProfile(),
            ControlProfile.createTabletProfile(),
            ControlProfile.createControllerProfile()
        )
    )
    val allProfiles: StateFlow<List<ControlProfile>> = _allProfiles.asStateFlow()

    private val _activeProfile = MutableStateFlow(ControlProfile.createDefaultProfile())
    val activeProfile: StateFlow<ControlProfile> = _activeProfile.asStateFlow()

    // Active orientation
    private val _orientation = MutableStateFlow(LayoutOrientation.LANDSCAPE)
    val orientation: StateFlow<LayoutOrientation> = _orientation.asStateFlow()

    // Current active layout
    private val _currentLayout = MutableStateFlow(_activeProfile.value.landscapeLayout)
    val currentLayout: StateFlow<ControlLayout> = _currentLayout.asStateFlow()

    // Editor state
    private val _selectedControlId = MutableStateFlow<String?>(null)
    val selectedControlId: StateFlow<String?> = _selectedControlId.asStateFlow()

    private val _isGridEnabled = MutableStateFlow(false)
    val isGridEnabled: StateFlow<Boolean> = _isGridEnabled.asStateFlow()

    private val _isSnapEnabled = MutableStateFlow(false)
    val isSnapEnabled: StateFlow<Boolean> = _isSnapEnabled.asStateFlow()

    private val _snapGridPercent = MutableStateFlow(0.05f)
    val snapGridPercent: StateFlow<Float> = _snapGridPercent.asStateFlow()

    // Editor history: layout snapshots for reliable undo/redo across drag, resize,
    // inspector edits, duplication, deletion, and layer changes.
    private val undoStack = java.util.ArrayDeque<ControlLayout>()
    private val redoStack = java.util.ArrayDeque<ControlLayout>()
    private val historyLock = Any()
    private val maxHistorySize = 80
    // A drag/resize can emit dozens of layout updates. Keep it as one undo step.
    @Volatile private var editorGestureBefore: ControlLayout? = null

    private val _canUndo = MutableStateFlow(false)
    val canUndo: StateFlow<Boolean> = _canUndo.asStateFlow()

    private val _canRedo = MutableStateFlow(false)
    val canRedo: StateFlow<Boolean> = _canRedo.asStateFlow()

    private fun refreshHistoryState() {
        synchronized(historyLock) {
            _canUndo.value = undoStack.isNotEmpty()
            _canRedo.value = redoStack.isNotEmpty()
        }
    }

    private fun recordHistory(before: ControlLayout) {
        synchronized(historyLock) {
            undoStack.addLast(before)
            while (undoStack.size > maxHistorySize) undoStack.removeFirst()
            redoStack.clear()
            _canUndo.value = undoStack.isNotEmpty()
            _canRedo.value = redoStack.isNotEmpty()
        }
    }

    private fun applyEditorLayout(layout: ControlLayout) {
        _currentLayout.value = layout
        val updatedProfile = _activeProfile.value.updateLayout(layout)
        _activeProfile.value = updatedProfile
        syncProfilesList(updatedProfile)
        saveActiveProfile()
    }

    fun undoEditorChange() {
        val previous = synchronized(historyLock) {
            if (undoStack.isEmpty()) return
            val current = _currentLayout.value
            redoStack.addLast(current)
            undoStack.removeLast().also { refreshHistoryState() }
        }
        applyEditorLayout(previous)
    }

    fun redoEditorChange() {
        val next = synchronized(historyLock) {
            if (redoStack.isEmpty()) return
            val current = _currentLayout.value
            undoStack.addLast(current)
            redoStack.removeLast().also { refreshHistoryState() }
        }
        applyEditorLayout(next)
    }

    // Legacy support
    private val _settings = MutableStateFlow(TouchSettings())
    val settings: StateFlow<TouchSettings> = _settings.asStateFlow()

    private val _legacyButtons = MutableStateFlow<Map<VirtualButtonType, VirtualButtonState>>(
        VirtualButtonType.entries.associateWith { VirtualButtonState(type = it) }
    )
    val buttons: StateFlow<Map<VirtualButtonType, VirtualButtonState>> = _legacyButtons.asStateFlow()

    // Joystick state (-1f to 1f)
    var joystickDeltaX: Float = 0f
        private set
    var joystickDeltaY: Float = 0f
        private set
    var isJoystickActive: Boolean = false
        private set

    init {
        scope.launch {
            storage?.let { store ->
                val loadedProfiles = store.loadAllProfiles()
                _allProfiles.value = loadedProfiles
                val activeId = store.getActiveProfileId()
                val profile = loadedProfiles.firstOrNull { it.id == activeId } ?: loadedProfiles.first()
                _activeProfile.value = profile
                _currentLayout.value = profile.getLayout(_orientation.value)
            }
        }
    }

    fun setOrientation(newOrientation: LayoutOrientation) {
        if (_orientation.value == newOrientation) return
        releaseAllInputs()
        _orientation.value = newOrientation
        _currentLayout.value = _activeProfile.value.getLayout(newOrientation)
    }

    fun selectControl(id: String?) {
        _selectedControlId.value = id
    }

    fun toggleGrid() {
        _isGridEnabled.value = !_isGridEnabled.value
    }

    fun toggleSnap() {
        _isSnapEnabled.value = !_isSnapEnabled.value
    }

    fun setSnapGridPercent(value: Float) {
        _snapGridPercent.value = value.coerceIn(0.01f, 0.20f)
    }

    fun beginEditorGesture() {
        if (editorGestureBefore == null) {
            editorGestureBefore = _currentLayout.value
        }
    }

    fun endEditorGesture() {
        val before = editorGestureBefore ?: return
        editorGestureBefore = null
        if (before != _currentLayout.value) {
            recordHistory(before)
        }
    }

    fun cancelEditorGesture() {
        val before = editorGestureBefore ?: return
        editorGestureBefore = null
        if (before != _currentLayout.value) {
            applyEditorLayout(before)
        }
    }

    fun updateControl(control: TouchControl) {
        val current = _currentLayout.value
        val updatedControl = if (_isSnapEnabled.value) {
            current.snap(control, _snapGridPercent.value)
        } else {
            control
        }
        val updatedLayout = current.updateControl(updatedControl)
        if (updatedLayout == current) return
        if (editorGestureBefore == null) {
            recordHistory(current)
        }
        applyEditorLayout(updatedLayout)
    }

    fun addControl(control: TouchControl) {
        val current = _currentLayout.value
        val updatedLayout = current.addControl(control)
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        _selectedControlId.value = control.id
    }

    fun deleteControl(id: String) {
        val current = _currentLayout.value
        val updatedLayout = current.removeControl(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        if (_selectedControlId.value == id) {
            _selectedControlId.value = null
        }
    }

    fun duplicateControl(id: String) {
        val current = _currentLayout.value
        val original = current.findControl(id) ?: return
        val updatedLayout = current.duplicateControl(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        val copy = updatedLayout.controls.lastOrNull { it.id != original.id && it.name == "${original.name} (Copy)" }
        _selectedControlId.value = copy?.id
    }

    fun bringControlToFront(id: String) {
        val current = _currentLayout.value
        val updatedLayout = current.bringToFront(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        _selectedControlId.value = id
    }

    fun sendControlToBack(id: String) {
        val current = _currentLayout.value
        val updatedLayout = current.sendToBack(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        _selectedControlId.value = id
    }

    fun moveControlUp(id: String) {
        val current = _currentLayout.value
        val updatedLayout = current.moveUp(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        _selectedControlId.value = id
    }

    fun moveControlDown(id: String) {
        val current = _currentLayout.value
        val updatedLayout = current.moveDown(id)
        if (updatedLayout == current) return
        recordHistory(current)
        applyEditorLayout(updatedLayout)
        _selectedControlId.value = id
    }

    fun resetSelectedControl(id: String) {
        val defaultProfile = ControlProfile.createDefaultProfile()
        val defaultControl = defaultProfile.getLayout(_orientation.value).findControl(id)
        if (defaultControl != null) {
            updateControl(defaultControl)
        }
    }

    fun resetCurrentProfileToDefault() {
        val defaultProfile = when (_activeProfile.value.id) {
            "pvp" -> ControlProfile.createPvpProfile()
            "survival" -> ControlProfile.createSurvivalProfile()
            "building" -> ControlProfile.createBuildingProfile()
            "tablet" -> ControlProfile.createTabletProfile()
            "controller" -> ControlProfile.createControllerProfile()
            else -> ControlProfile.createDefaultProfile().copy(id = _activeProfile.value.id, name = _activeProfile.value.name)
        }
        _activeProfile.value = defaultProfile
        _currentLayout.value = defaultProfile.getLayout(_orientation.value)
        syncProfilesList(defaultProfile)
        saveActiveProfile()
    }

    fun resetToSafeArea() {
        val safeLayout = _currentLayout.value.resetToSafeArea()
        _currentLayout.value = safeLayout

        val updatedProfile = _activeProfile.value.updateLayout(safeLayout)
        _activeProfile.value = updatedProfile
        syncProfilesList(updatedProfile)
        saveActiveProfile()
    }

    fun switchProfile(profileId: String) {
        val profile = _allProfiles.value.firstOrNull { it.id == profileId } ?: return
        _activeProfile.value = profile
        _currentLayout.value = profile.getLayout(_orientation.value)
        _selectedControlId.value = null
        saveActiveProfile()
    }

    fun createNewProfile(name: String, baseProfileId: String? = null): ControlProfile {
        val base = _allProfiles.value.firstOrNull { it.id == baseProfileId } ?: _activeProfile.value
        val newProfile = base.copy(
            id = "custom_${System.currentTimeMillis()}",
            name = name,
            isCustom = true
        )
        val list = _allProfiles.value + newProfile
        _allProfiles.value = list
        switchProfile(newProfile.id)
        saveActiveProfile()
        return newProfile
    }

    fun renameProfile(id: String, newName: String) {
        val list = _allProfiles.value.map {
            if (it.id == id) it.copy(name = newName) else it
        }
        _allProfiles.value = list
        if (_activeProfile.value.id == id) {
            _activeProfile.value = _activeProfile.value.copy(name = newName)
        }
        saveActiveProfile()
    }

    fun deleteProfile(id: String) {
        // Do not allow deleting the last profile
        if (_allProfiles.value.size <= 1) return
        val list = _allProfiles.value.filterNot { it.id == id }
        _allProfiles.value = list
        if (_activeProfile.value.id == id) {
            val fallback = list.first()
            switchProfile(fallback.id)
        }
        saveActiveProfile()
    }

    fun duplicateProfile(id: String): ControlProfile {
        val original = _allProfiles.value.firstOrNull { it.id == id } ?: _activeProfile.value
        val duplicated = original.copy(
            id = "custom_${System.currentTimeMillis()}",
            name = "${original.name} (Copy)",
            isCustom = true
        )
        val list = _allProfiles.value + duplicated
        _allProfiles.value = list
        switchProfile(duplicated.id)
        saveActiveProfile()
        return duplicated
    }

    fun exportActiveProfile(): String {
        return storage?.exportProfileToJson(_activeProfile.value) ?: _activeProfile.value.toJson().toString(2)
    }

    fun importProfile(jsonStr: String): Result<ControlProfile> {
        return try {
            val store = storage ?: ControlLayoutStorage(context ?: throw IllegalStateException("Storage unavailable"))
            val imported = store.validateAndImportProfile(jsonStr)
            val list = _allProfiles.value + imported
            _allProfiles.value = list
            switchProfile(imported.id)
            saveActiveProfile()
            Result.success(imported)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    fun saveActiveProfile() {
        val store = storage ?: return
        synchronized(saveLock) {
            saveJob?.cancel()
            val profilesSnapshot = _allProfiles.value.toList()
            val activeIdSnapshot = _activeProfile.value.id
            saveJob = scope.launch {
                delay(120)
                store.saveState(profilesSnapshot, activeIdSnapshot)
            }
        }
    }

    private fun syncProfilesList(updated: ControlProfile) {
        val updatedList = _allProfiles.value.map {
            if (it.id == updated.id) updated else it
        }
        _allProfiles.value = updatedList
    }

    // ==========================================
    // MULTI-TOUCH IN-GAME INPUT DISPATCH
    // ==========================================

    /**
     * Creates a launcher-owned pointer token. Compose's high-level gesture APIs do not
     * expose MotionEvent pointer IDs, so we use monotonic tokens rather than timestamps
     * or object identity. This guarantees independent simultaneous controls get unique
     * ownership for the lifetime of their gesture.
     */
    fun allocatePointerToken(): Int {
        while (true) {
            val token = nextPointerToken.getAndIncrement()
            if (token > 0) return token
            nextPointerToken.compareAndSet(token, 1)
        }
    }

    fun onControlPointerDown(control: TouchControl, pointerId: Int) {
        if (pointerToControlMap.putIfAbsent(pointerId, control.id) != null) return
        val set = _pressedControlIds.value.toMutableSet()
        set.add(control.id)
        _pressedControlIds.value = set

        inputMapper.handleControlPress(control, true)
    }

    fun onControlPointerUp(pointerId: Int) {
        val controlId = pointerToControlMap.remove(pointerId) ?: return
        // Check if any other pointer is still pressing this control
        if (!pointerToControlMap.values.contains(controlId)) {
            val set = _pressedControlIds.value.toMutableSet()
            set.remove(controlId)
            _pressedControlIds.value = set

            val control = _currentLayout.value.findControl(controlId)
            if (control != null) {
                inputMapper.handleControlPress(control, false)
            }
        }
    }

    fun onJoystickMove(deltaX: Float, deltaY: Float, maxRadius: Float, deadZone: Float) {
        val dist = sqrt(deltaX * deltaX + deltaY * deltaY)
        if (dist <= 0.01f) {
            joystickDeltaX = 0f
            joystickDeltaY = 0f
            isJoystickActive = false
            inputMapper.releaseJoystick()
            return
        }

        val clampedDist = dist.coerceAtMost(maxRadius)
        val angle = atan2(deltaY, deltaX)
        joystickDeltaX = (cos(angle) * (clampedDist / maxRadius)).coerceIn(-1f, 1f)
        joystickDeltaY = (sin(angle) * (clampedDist / maxRadius)).coerceIn(-1f, 1f)
        isJoystickActive = true

        inputMapper.handleJoystick(deltaX, deltaY, maxRadius, deadZone)
    }

    fun onJoystickRelease() {
        joystickDeltaX = 0f
        joystickDeltaY = 0f
        isJoystickActive = false
        inputMapper.releaseJoystick()
    }

    fun onCameraLook(deltaX: Float, deltaY: Float, sensitivity: Float, invertY: Boolean, hSens: Float, vSens: Float) {
        inputMapper.handleCameraLook(deltaX, deltaY, sensitivity, invertY, hSens, vSens)
    }

    /** Release all active virtual pointers before switching surfaces/profiles. */
    /**
     * Physical Android-touch state is routed through the same InputBridge as virtual
     * controls. Only the primary pointer owns the camera/mouse cursor; secondary
     * pointers remain reserved for multi-touch gestures and never release the primary
     * pointer's buttons.
     */
    private val physicalTouchPointers = ConcurrentHashMap<Int, Boolean>()
    private var physicalPrimaryPointer: Int? = null

    fun onPhysicalTouchDown(pointerId: Int, x: Float, y: Float) {
        if (physicalTouchPointers.putIfAbsent(pointerId, true) != null) return
        if (physicalPrimaryPointer == null) {
            physicalPrimaryPointer = pointerId
            inputBridge.mouse.setCursorPosition(x, y)
        }
    }

    fun onPhysicalTouchMove(pointerId: Int, x: Float, y: Float, deltaX: Float, deltaY: Float) {
        if (!physicalTouchPointers.containsKey(pointerId) || physicalPrimaryPointer != pointerId) return
        inputBridge.mouse.setCursorPosition(x, y)
        if (deltaX != 0f || deltaY != 0f) {
            inputMapper.handleCameraLook(deltaX, deltaY, 1f, false, 1f, 1f)
        }
    }

    fun onPhysicalTouchButton(pointerId: Int, button: Int, isDown: Boolean) {
        if (!physicalTouchPointers.containsKey(pointerId)) return
        inputBridge.mouse.sendVirtualMouseButton("physical-touch-$pointerId", button, isDown)
    }

    fun onPhysicalTouchUp(pointerId: Int, x: Float, y: Float) {
        if (physicalTouchPointers.remove(pointerId) == null) return
        inputBridge.releaseVirtualSource("physical-touch-$pointerId")
        if (physicalPrimaryPointer == pointerId) {
            physicalPrimaryPointer = physicalTouchPointers.keys.minOrNull()
            physicalPrimaryPointer?.let {
                inputBridge.mouse.setCursorPosition(x, y)
            }
        }
    }

    fun releaseAllPhysicalTouches() {
        physicalTouchPointers.keys.toList().forEach { pointerId ->
            inputBridge.releaseVirtualSource("physical-touch-$pointerId")
        }
        physicalTouchPointers.clear()
        physicalPrimaryPointer = null
    }

    fun releaseAllControlPointers() {
        releaseAllPhysicalTouches()
        val activeControlIds = pointerToControlMap.values.toSet()
        pointerToControlMap.clear()
        val pressed = _pressedControlIds.value
        _pressedControlIds.value = emptySet()
        activeControlIds.forEach { controlId ->
            _currentLayout.value.findControl(controlId)?.let {
                inputMapper.handleControlPress(it, false)
            }
        }
        if (pressed.isNotEmpty() && activeControlIds.isEmpty()) {
            inputMapper.releaseAll()
        }
    }

    fun releaseAllInputs() {
        releaseAllControlPointers()
        _pressedControlIds.value = emptySet()
        joystickDeltaX = 0f
        joystickDeltaY = 0f
        isJoystickActive = false
        inputMapper.releaseAll()
    }

    // ==========================================
    // LEGACY METHODS (Preserved for compatibility)
    // ==========================================

    fun setButtonPressed(type: VirtualButtonType, pressed: Boolean) {
        val current = _legacyButtons.value.toMutableMap()
        val btn = current[type] ?: VirtualButtonState(type)
        current[type] = btn.copy(isPressed = pressed)
        _legacyButtons.value = current

        // Also route to input bridge
        when (type) {
            VirtualButtonType.ATTACK -> inputBridge.mouse.sendMouseButton(0, pressed)
            VirtualButtonType.USE -> inputBridge.mouse.sendMouseButton(1, pressed)
            else -> inputBridge.keyboard.sendKeyEvent(type.keyCode, pressed)
        }
    }

    fun updateButtonPosition(type: VirtualButtonType, xPercent: Float, yPercent: Float) {
        val current = _legacyButtons.value.toMutableMap()
        val btn = current[type] ?: VirtualButtonState(type)
        current[type] = btn.copy(
            xPercent = xPercent.coerceIn(0.02f, 0.98f),
            yPercent = yPercent.coerceIn(0.02f, 0.98f)
        )
        _legacyButtons.value = current
    }

    fun updateSettings(opacity: Float? = null, scale: Float? = null, sensitivity: Float? = null, invertY: Boolean? = null, virtualMouse: Boolean? = null) {
        val curr = _settings.value
        _settings.value = curr.copy(
            opacity = opacity ?: curr.opacity,
            buttonScale = scale ?: curr.buttonScale,
            mouseSensitivity = sensitivity ?: curr.mouseSensitivity,
            invertY = invertY ?: curr.invertY,
            virtualMouseEnabled = virtualMouse ?: curr.virtualMouseEnabled
        )
    }

    fun resetToDefaults() {
        _legacyButtons.value = VirtualButtonType.entries.associateWith { VirtualButtonState(type = it) }
        resetCurrentProfileToDefault()
    }

    fun applySerializedPositions(serialized: String) {
        if (serialized.isBlank()) return
        val updated = _legacyButtons.value.toMutableMap()
        serialized.split(";").forEachIndexed { index, token ->
            val parts = token.split(":")
            if (parts.size != 3) {
                LauncherLogger.warn("Ignoring malformed legacy button layout entry $index")
                return@forEachIndexed
            }
            val type = runCatching { VirtualButtonType.valueOf(parts[0]) }.getOrNull()
            val x = parts[1].toFloatOrNull()
            val y = parts[2].toFloatOrNull()
            if (type == null || x == null || y == null) {
                LauncherLogger.warn("Ignoring malformed legacy button layout entry $index")
                return@forEachIndexed
            }
            updated[type] = (updated[type] ?: VirtualButtonState(type)).copy(
                xPercent = x.coerceIn(0.02f, 0.98f),
                yPercent = y.coerceIn(0.02f, 0.98f)
            )
        }
        _legacyButtons.value = updated
    }

    fun getSerializedPositions(): String {
        return _legacyButtons.value.values.joinToString(";") { "${it.type.name}:${it.xPercent}:${it.yPercent}" }
    }

    fun updateJoystick(touchX: Float, touchY: Float, centerX: Float, centerY: Float, maxRadius: Float) {
        onJoystickMove(touchX - centerX, touchY - centerY, maxRadius, 0.15f)
    }

    fun releaseJoystick() {
        onJoystickRelease()
    }
}
