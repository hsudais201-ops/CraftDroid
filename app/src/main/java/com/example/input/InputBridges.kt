package com.example.input

import com.example.game.NativeGameBridge
import com.example.logs.LauncherLogger
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.util.concurrent.ConcurrentHashMap

class KeyboardInputBridge {
    private val sourceKeys = ConcurrentHashMap<String, MutableSet<Int>>()
    private val keyOwners = ConcurrentHashMap<Int, MutableSet<String>>()

    @Synchronized
    private fun setKeySource(source: String, keyCode: Int, down: Boolean, modifiers: Int = 0) {
        if (keyCode == MinecraftKeyCodes.KEY_UNKNOWN) return
        val owners = keyOwners.computeIfAbsent(keyCode) { LinkedHashSet() }
        val sourceSet = sourceKeys.computeIfAbsent(source) { LinkedHashSet() }
        val wasOwned = sourceSet.contains(keyCode)
        if (wasOwned == down) return

        if (down) {
            sourceSet.add(keyCode)
            val wasGloballyDown = owners.isNotEmpty()
            owners.add(source)
            if (!wasGloballyDown) NativeGameBridge.sendKey(keyCode, true, modifiers)
        } else {
            sourceSet.remove(keyCode)
            if (sourceSet.isEmpty()) sourceKeys.remove(source)
            owners.remove(source)
            if (owners.isEmpty()) {
                keyOwners.remove(keyCode)
                NativeGameBridge.sendKey(keyCode, false, modifiers)
            }
        }
    }

    fun sendKeyEvent(keyCode: Int, isDown: Boolean) = setKeySource("physical", keyCode, isDown)
    fun sendKeyEventWithModifiers(keyCode: Int, isDown: Boolean, modifiers: Int) = setKeySource("physical", keyCode, isDown, modifiers)
    fun sendVirtualKey(source: String, keyCode: Int, isDown: Boolean) = setKeySource("virtual:$source", keyCode, isDown)

    fun isKeyDown(keyCode: Int): Boolean = keyOwners[keyCode]?.isNotEmpty() == true

    @Synchronized fun releaseSource(source: String) {
        sourceKeys[source]?.toList().orEmpty().forEach { setKeySource(source, it, false) }
        sourceKeys.remove(source)
    }

    fun releaseAllKeys() {
        sourceKeys.keys.toList().forEach { releaseSource(it) }
        sourceKeys.clear()
        keyOwners.clear()
    }
}

class MouseInputBridge {
    private val sourceButtons = ConcurrentHashMap<String, MutableSet<Int>>()
    private val buttonOwners = ConcurrentHashMap<Int, MutableSet<String>>()
    private val _cursorPosition = MutableStateFlow(Pair(500f, 300f))
    val cursorPosition: StateFlow<Pair<Float, Float>> = _cursorPosition.asStateFlow()

    @Synchronized
    private fun setButtonSource(source: String, button: Int, down: Boolean) {
        val owners = buttonOwners.computeIfAbsent(button) { LinkedHashSet() }
        val sourceSet = sourceButtons.computeIfAbsent(source) { LinkedHashSet() }
        val wasOwned = sourceSet.contains(button)
        if (wasOwned == down) return
        val p = _cursorPosition.value
        if (down) {
            sourceSet.add(button)
            val wasGloballyDown = owners.isNotEmpty()
            owners.add(source)
            if (!wasGloballyDown) NativeGameBridge.sendMouse(p.first, p.second, 0f, 0f, button, true)
        } else {
            sourceSet.remove(button)
            if (sourceSet.isEmpty()) sourceButtons.remove(source)
            owners.remove(source)
            if (owners.isEmpty()) {
                buttonOwners.remove(button)
                NativeGameBridge.sendMouse(p.first, p.second, 0f, 0f, button, false)
            }
        }
    }

    fun sendMouseButton(button: Int, isDown: Boolean) = setButtonSource("physical", button, isDown)
    fun sendVirtualMouseButton(source: String, button: Int, isDown: Boolean) = setButtonSource("virtual:$source", button, isDown)
    fun isButtonDown(button: Int): Boolean = buttonOwners[button]?.isNotEmpty() == true

    fun setCursorPosition(x: Float, y: Float) { _cursorPosition.value = Pair(x, y) }

    fun sendMouseMove(deltaX: Float, deltaY: Float) {
        if (deltaX == 0f && deltaY == 0f) return
        val current = _cursorPosition.value
        val next = Pair(current.first + deltaX, current.second + deltaY)
        _cursorPosition.value = next
        NativeGameBridge.sendMouse(next.first, next.second, deltaX, deltaY, -1, false)
    }

    fun sendMouseScroll(deltaY: Float, deltaX: Float = 0f) {
        if (deltaY == 0f && deltaX == 0f) return
        NativeGameBridge.sendMouseScroll(deltaX, deltaY)
    }

    @Synchronized fun releaseSource(source: String) {
        sourceButtons[source]?.toList().orEmpty().forEach { setButtonSource(source, it, false) }
        sourceButtons.remove(source)
    }

    fun releaseAllButtons() {
        sourceButtons.keys.toList().forEach { releaseSource(it) }
        sourceButtons.clear()
        buttonOwners.clear()
    }
}

class GamepadInputBridge {
    fun sendAxis(axis: Int, value: Float) { NativeGameBridge.sendGamepad(axis, value) }
    fun sendButton(button: Int, isDown: Boolean) { NativeGameBridge.sendGamepadButton(button, isDown) }
}

class InputBridge(
    val keyboard: KeyboardInputBridge = KeyboardInputBridge(),
    val mouse: MouseInputBridge = MouseInputBridge(),
    val gamepad: GamepadInputBridge = GamepadInputBridge()
) {
    fun releaseVirtualSource(source: String) {
        keyboard.releaseSource("virtual:$source")
        mouse.releaseSource("virtual:$source")
    }
    fun releaseAll() { keyboard.releaseAllKeys(); mouse.releaseAllButtons() }
    fun diagnostics(): String = NativeGameBridge.inputDiagnostics()
}
