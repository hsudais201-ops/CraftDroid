package com.example.input

// GLFW Desktop Keycodes used by Minecraft Java Edition
object MinecraftKeyCodes {
    const val KEY_UNKNOWN = -1
    const val KEY_SPACE = 32
    const val KEY_0 = 48
    const val KEY_1 = 49
    const val KEY_2 = 50
    const val KEY_3 = 51
    const val KEY_4 = 52
    const val KEY_5 = 53
    const val KEY_6 = 54
    const val KEY_7 = 55
    const val KEY_8 = 56
    const val KEY_9 = 57
    const val KEY_A = 65
    const val KEY_B = 66
    const val KEY_C = 67
    const val KEY_D = 68
    const val KEY_E = 69
    const val KEY_F = 70
    const val KEY_Q = 81
    const val KEY_S = 83
    const val KEY_T = 84
    const val KEY_W = 87
    const val KEY_ESCAPE = 256
    const val KEY_ENTER = 257
    const val KEY_TAB = 258
    const val KEY_BACKSPACE = 259
    const val KEY_F3 = 292
    const val KEY_F5 = 294
    const val KEY_LEFT_SHIFT = 340
    const val KEY_LEFT_CONTROL = 341
    const val KEY_LEFT_ALT = 342

    const val MOUSE_BUTTON_LEFT = 0
    const val MOUSE_BUTTON_RIGHT = 1
    const val MOUSE_BUTTON_MIDDLE = 2
}

enum class VirtualButtonType(
    val label: String,
    val keyCode: Int,
    val defaultXPercent: Float,
    val defaultYPercent: Float,
    val isMouse: Boolean = false
) {
    ATTACK("PRI", MinecraftKeyCodes.MOUSE_BUTTON_LEFT, 0.88f, 0.52f, isMouse = true),
    USE("SEC", MinecraftKeyCodes.MOUSE_BUTTON_RIGHT, 0.76f, 0.52f, isMouse = true),
    JUMP("JUMP", MinecraftKeyCodes.KEY_SPACE, 0.88f, 0.72f),
    SNEAK("SNEAK", MinecraftKeyCodes.KEY_LEFT_SHIFT, 0.76f, 0.72f),
    SPRINT("SPRINT", MinecraftKeyCodes.KEY_LEFT_CONTROL, 0.12f, 0.40f),
    INVENTORY("INV", MinecraftKeyCodes.KEY_E, 0.50f, 0.85f),
    DROP("DROP", MinecraftKeyCodes.KEY_Q, 0.12f, 0.52f),
    CHAT("CHAT", MinecraftKeyCodes.KEY_T, 0.65f, 0.08f),
    DEBUG("F3", MinecraftKeyCodes.KEY_F3, 0.50f, 0.08f),
    PERSPECTIVE("F5", MinecraftKeyCodes.KEY_F5, 0.35f, 0.08f),
    PAUSE("ESC", MinecraftKeyCodes.KEY_ESCAPE, 0.06f, 0.08f)
}

data class VirtualButtonState(
    val type: VirtualButtonType,
    val isPressed: Boolean = false,
    val xPercent: Float = type.defaultXPercent,
    val yPercent: Float = type.defaultYPercent,
    val sizeDp: Int = 56
)

data class TouchSettings(
    val opacity: Float = 0.75f,
    val buttonScale: Float = 1.0f,
    val mouseSensitivity: Float = 1.0f,
    val invertY: Boolean = false,
    val virtualMouseEnabled: Boolean = false
)

data class ControllerMapping(
    val buttonA: Int = MinecraftKeyCodes.KEY_SPACE, // Jump
    val buttonB: Int = MinecraftKeyCodes.KEY_LEFT_SHIFT, // Sneak
    val buttonX: Int = MinecraftKeyCodes.KEY_E, // Inventory
    val buttonY: Int = MinecraftKeyCodes.KEY_Q, // Drop
    val leftTrigger: Int = MinecraftKeyCodes.MOUSE_BUTTON_RIGHT, // Use
    val rightTrigger: Int = MinecraftKeyCodes.MOUSE_BUTTON_LEFT, // Attack
    val leftBumper: Int = MinecraftKeyCodes.KEY_LEFT_CONTROL, // Sprint
    val rightBumper: Int = MinecraftKeyCodes.KEY_F5 // Perspective
)
