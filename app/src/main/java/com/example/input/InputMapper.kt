package com.example.input

import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Maps TouchControl inputs into standard Minecraft GLFW keyboard and mouse events.
 */
class InputMapper(
    private val bridge: InputBridge
) {
    // Track keys pressed by joystick so we can release them properly on changes
    private var joystickForwardDown = false
    private var joystickBackwardDown = false
    private var joystickLeftDown = false
    private var joystickRightDown = false

    fun handleControlPress(control: TouchControl, isPressed: Boolean) {
        val action = control.action
        if (action.isMouse) {
            bridge.mouse.sendVirtualMouseButton(control.id, action.mouseButton, isPressed)
        } else {
            val keyCode = if (action == ControlAction.CUSTOM_KEY) control.keyBinding else action.defaultKeyCode
            if (keyCode != MinecraftKeyCodes.KEY_UNKNOWN) {
                bridge.keyboard.sendVirtualKey(control.id, keyCode, isPressed)
            }
        }
    }

    fun handleJoystick(
        deltaX: Float,
        deltaY: Float,
        maxRadius: Float,
        deadZone: Float
    ) {
        val dist = sqrt(deltaX * deltaX + deltaY * deltaY)
        val normalizedDist = (dist / maxRadius).coerceIn(0f, 1f)

        if (normalizedDist < deadZone) {
            releaseJoystick()
            return
        }

        // Angle in radians (-PI to PI), 0 is right, PI/2 is down, -PI/2 is up
        val angle = atan2(deltaY, deltaX)
        val deg = Math.toDegrees(angle.toDouble())

        // Forward (W): deg between -157.5 and -22.5
        val forward = deg in -157.5..-22.5
        // Backward (S): deg between 22.5 and 157.5
        val backward = deg in 22.5..157.5
        // Left (A): abs(deg) > 112.5
        val left = abs(deg) > 112.5
        // Right (D): abs(deg) < 67.5
        val right = abs(deg) < 67.5

        if (forward != joystickForwardDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_W, forward)
            joystickForwardDown = forward
        }
        if (backward != joystickBackwardDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_S, backward)
            joystickBackwardDown = backward
        }
        if (left != joystickLeftDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_A, left)
            joystickLeftDown = left
        }
        if (right != joystickRightDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_D, right)
            joystickRightDown = right
        }
    }

    fun releaseJoystick() {
        if (joystickForwardDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_W, false)
            joystickForwardDown = false
        }
        if (joystickBackwardDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_S, false)
            joystickBackwardDown = false
        }
        if (joystickLeftDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_A, false)
            joystickLeftDown = false
        }
        if (joystickRightDown) {
            bridge.keyboard.sendVirtualKey("joystick", MinecraftKeyCodes.KEY_D, false)
            joystickRightDown = false
        }
    }

    fun handleCameraLook(
        deltaX: Float,
        deltaY: Float,
        sensitivity: Float,
        invertY: Boolean,
        horizontalSens: Float = 1.0f,
        verticalSens: Float = 1.0f
    ) {
        val dx = deltaX * sensitivity * horizontalSens
        val dy = deltaY * sensitivity * verticalSens * (if (invertY) -1.0f else 1.0f)
        bridge.mouse.sendMouseMove(dx, dy)
    }

    fun releaseAll() {
        releaseJoystick()
        bridge.releaseAll()
    }
}
