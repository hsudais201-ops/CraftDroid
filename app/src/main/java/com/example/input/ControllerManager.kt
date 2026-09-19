package com.example.input

import android.view.KeyEvent
import android.view.MotionEvent
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

data class GamepadState(
    val leftStickX: Float = 0f,
    val leftStickY: Float = 0f,
    val rightStickX: Float = 0f,
    val rightStickY: Float = 0f,
    val isConnected: Boolean = false
)

class ControllerManager {

    private val _mapping = MutableStateFlow(ControllerMapping())
    val mapping: StateFlow<ControllerMapping> = _mapping.asStateFlow()

    private val _gamepadState = MutableStateFlow(GamepadState())
    val gamepadState: StateFlow<GamepadState> = _gamepadState.asStateFlow()

    fun updateMapping(newMapping: ControllerMapping) {
        _mapping.value = newMapping
    }

    fun handleKeyEvent(event: KeyEvent): Int? {
        val mapping = _mapping.value
        val isDown = event.action == KeyEvent.ACTION_DOWN
        return when (event.keyCode) {
            KeyEvent.KEYCODE_BUTTON_A -> mapping.buttonA
            KeyEvent.KEYCODE_BUTTON_B -> mapping.buttonB
            KeyEvent.KEYCODE_BUTTON_X -> mapping.buttonX
            KeyEvent.KEYCODE_BUTTON_Y -> mapping.buttonY
            KeyEvent.KEYCODE_BUTTON_L1 -> mapping.leftBumper
            KeyEvent.KEYCODE_BUTTON_R1 -> mapping.rightBumper
            else -> null
        }
    }

    fun handleGenericMotionEvent(event: MotionEvent) {
        val lx = event.getAxisValue(MotionEvent.AXIS_X)
        val ly = event.getAxisValue(MotionEvent.AXIS_Y)
        val rx = event.getAxisValue(MotionEvent.AXIS_Z)
        val ry = event.getAxisValue(MotionEvent.AXIS_RZ)

        _gamepadState.value = GamepadState(
            leftStickX = if (Math.abs(lx) > 0.15f) lx else 0f,
            leftStickY = if (Math.abs(ly) > 0.15f) ly else 0f,
            rightStickX = if (Math.abs(rx) > 0.15f) rx else 0f,
            rightStickY = if (Math.abs(ry) > 0.15f) ry else 0f,
            isConnected = true
        )
    }
}
