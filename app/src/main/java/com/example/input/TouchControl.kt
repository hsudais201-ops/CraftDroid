package com.example.input

import org.json.JSONObject
import java.util.UUID

data class TouchControl(
    val id: String = UUID.randomUUID().toString().take(8),
    val name: String,
    val type: ControlType = ControlType.BUTTON,
    val action: ControlAction,
    val xPercent: Float,
    val yPercent: Float,
    val widthDp: Int = 56,
    val heightDp: Int = 56,
    val sizeScale: Float = 1.0f,
    val opacity: Float = 0.8f,
    val visible: Boolean = true,
    val shape: ButtonShape = ButtonShape.MINECRAFT_STYLE,
    val cornerRadiusDp: Int = 8,
    val hasBorder: Boolean = true,
    val hasShadow: Boolean = true,
    val keyBinding: Int = action.defaultKeyCode,
    val customLabel: String? = null,
    // Joystick specific settings
    val joystickDeadZone: Float = 0.15f,
    val joystickMaxRadiusDp: Float = 65f,
    val joystickSensitivity: Float = 1.0f,
    // When enabled, the joystick origin follows the initial finger-down point.
    val joystickDynamicOrigin: Boolean = false,
    // Camera specific settings
    val cameraSensitivity: Float = 1.0f,
    val cameraInvertY: Boolean = false,
    val cameraHorizontalSens: Float = 1.0f,
    val cameraVerticalSens: Float = 1.0f,
    val cameraSmoothing: Float = 0.0f
) {
    val displayLabel: String
        get() = customLabel?.ifBlank { null } ?: action.defaultLabel

    val effectiveWidthDp: Float
        get() = widthDp * sizeScale

    val effectiveHeightDp: Float
        get() = heightDp * sizeScale

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("id", id)
            put("name", name)
            put("type", type.name)
            put("action", action.name)
            put("xPercent", xPercent.toDouble())
            put("yPercent", yPercent.toDouble())
            put("widthDp", widthDp)
            put("heightDp", heightDp)
            put("sizeScale", sizeScale.toDouble())
            put("opacity", opacity.toDouble())
            put("visible", visible)
            put("shape", shape.name)
            put("cornerRadiusDp", cornerRadiusDp)
            put("hasBorder", hasBorder)
            put("hasShadow", hasShadow)
            put("keyBinding", keyBinding)
            put("customLabel", customLabel ?: "")
            put("joystickDeadZone", joystickDeadZone.toDouble())
            put("joystickMaxRadiusDp", joystickMaxRadiusDp.toDouble())
            put("joystickSensitivity", joystickSensitivity.toDouble())
            put("joystickDynamicOrigin", joystickDynamicOrigin)
            put("cameraSensitivity", cameraSensitivity.toDouble())
            put("cameraInvertY", cameraInvertY)
            put("cameraHorizontalSens", cameraHorizontalSens.toDouble())
            put("cameraVerticalSens", cameraVerticalSens.toDouble())
            put("cameraSmoothing", cameraSmoothing.toDouble())
        }
    }

    companion object {
        fun fromJson(json: JSONObject): TouchControl {
            val id = json.optString("id", UUID.randomUUID().toString().take(8))
            val action = ControlAction.fromName(json.optString("action", ControlAction.JUMP.name))
            val type = try {
                ControlType.valueOf(json.optString("type", ControlType.BUTTON.name))
            } catch (_: Exception) {
                ControlType.BUTTON
            }
            val shape = try {
                ButtonShape.valueOf(json.optString("shape", ButtonShape.MINECRAFT_STYLE.name))
            } catch (_: Exception) {
                ButtonShape.MINECRAFT_STYLE
            }

            return TouchControl(
                id = id,
                name = json.optString("name", action.actionName),
                type = type,
                action = action,
                xPercent = json.optDouble("xPercent", 0.5).toFloat().coerceIn(0.01f, 0.99f),
                yPercent = json.optDouble("yPercent", 0.5).toFloat().coerceIn(0.01f, 0.99f),
                widthDp = json.optInt("widthDp", 56).coerceIn(24, 400),
                heightDp = json.optInt("heightDp", 56).coerceIn(24, 400),
                sizeScale = json.optDouble("sizeScale", 1.0).toFloat().coerceIn(0.5f, 2.0f),
                opacity = json.optDouble("opacity", 0.8).toFloat().coerceIn(0.0f, 1.0f),
                visible = json.optBoolean("visible", true),
                shape = shape,
                cornerRadiusDp = json.optInt("cornerRadiusDp", 8).coerceIn(0, 50),
                hasBorder = json.optBoolean("hasBorder", true),
                hasShadow = json.optBoolean("hasShadow", true),
                keyBinding = json.optInt("keyBinding", action.defaultKeyCode),
                customLabel = json.optString("customLabel", "").takeIf { it.isNotBlank() },
                joystickDeadZone = json.optDouble("joystickDeadZone", 0.15).toFloat().coerceIn(0.05f, 0.4f),
                joystickMaxRadiusDp = json.optDouble("joystickMaxRadiusDp", 65.0).toFloat().coerceIn(30f, 120f),
                joystickSensitivity = json.optDouble("joystickSensitivity", 1.0).toFloat().coerceIn(0.2f, 3.0f),
                joystickDynamicOrigin = json.optBoolean("joystickDynamicOrigin", false),
                cameraSensitivity = json.optDouble("cameraSensitivity", 1.0).toFloat().coerceIn(0.1f, 5.0f),
                cameraInvertY = json.optBoolean("cameraInvertY", false),
                cameraHorizontalSens = json.optDouble("cameraHorizontalSens", 1.0).toFloat().coerceIn(0.1f, 5.0f),
                cameraVerticalSens = json.optDouble("cameraVerticalSens", 1.0).toFloat().coerceIn(0.1f, 5.0f),
                cameraSmoothing = json.optDouble("cameraSmoothing", 0.0).toFloat().coerceIn(0.0f, 1.0f)
            )
        }
    }
}
