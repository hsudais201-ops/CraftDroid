package com.example.input

enum class ControlType(val displayName: String) {
    BUTTON("Button"),
    JOYSTICK("Movement Joystick"),
    TOUCH_AREA("Camera / Look Area"),
    HOTBAR_SLOT("Hotbar Slot"),
    KEYBOARD_KEY("Keyboard Key")
}

enum class ButtonShape(val displayName: String) {
    MINECRAFT_STYLE("Minecraft-style"),
    CIRCLE("Circle"),
    SQUARE("Square"),
    ROUNDED("Rounded"),
    TRANSPARENT("Transparent"),
    MINIMAL("Minimal")
}

enum class ControlCategory(val displayName: String) {
    MOVEMENT("Movement"),
    ACTION("Action"),
    CAMERA("Camera"),
    HOTBAR("Hotbar"),
    OTHER("Other")
}

enum class ControlAction(
    val actionName: String,
    val defaultLabel: String,
    val category: ControlCategory,
    val defaultKeyCode: Int,
    val isMouse: Boolean = false,
    val mouseButton: Int = -1 // 0 = Left, 1 = Right, 2 = Middle
) {
    // MOVEMENT
    FORWARD("Forward", "W", ControlCategory.MOVEMENT, MinecraftKeyCodes.KEY_W),
    BACKWARD("Backward", "S", ControlCategory.MOVEMENT, MinecraftKeyCodes.KEY_S),
    LEFT("Left", "A", ControlCategory.MOVEMENT, MinecraftKeyCodes.KEY_A),
    RIGHT("Right", "D", ControlCategory.MOVEMENT, MinecraftKeyCodes.KEY_D),
    JOYSTICK_MOVE("Movement Joystick", "JOY", ControlCategory.MOVEMENT, MinecraftKeyCodes.KEY_UNKNOWN),

    // ACTION
    JUMP("Jump", "JUMP", ControlCategory.ACTION, MinecraftKeyCodes.KEY_SPACE),
    SNEAK("Sneak", "SNEAK", ControlCategory.ACTION, MinecraftKeyCodes.KEY_LEFT_SHIFT),
    SPRINT("Sprint", "SPRINT", ControlCategory.ACTION, MinecraftKeyCodes.KEY_LEFT_CONTROL),
    ATTACK("Attack / Break", "PRI", ControlCategory.ACTION, MinecraftKeyCodes.KEY_UNKNOWN, isMouse = true, mouseButton = MinecraftKeyCodes.MOUSE_BUTTON_LEFT),
    USE("Use / Place", "SEC", ControlCategory.ACTION, MinecraftKeyCodes.KEY_UNKNOWN, isMouse = true, mouseButton = MinecraftKeyCodes.MOUSE_BUTTON_RIGHT),
    DROP("Drop Item", "DROP", ControlCategory.ACTION, MinecraftKeyCodes.KEY_Q),
    INVENTORY("Inventory", "INV", ControlCategory.ACTION, MinecraftKeyCodes.KEY_E),
    CHAT("Chat", "CHAT", ControlCategory.ACTION, MinecraftKeyCodes.KEY_T),
    PAUSE("Pause / Menu", "ESC", ControlCategory.ACTION, MinecraftKeyCodes.KEY_ESCAPE),

    // CAMERA
    CAMERA_LOOK("Camera / Look Area", "LOOK", ControlCategory.CAMERA, MinecraftKeyCodes.KEY_UNKNOWN),

    // HOTBAR
    HOTBAR_1("Hotbar Slot 1", "1", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_1),
    HOTBAR_2("Hotbar Slot 2", "2", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_2),
    HOTBAR_3("Hotbar Slot 3", "3", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_3),
    HOTBAR_4("Hotbar Slot 4", "4", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_4),
    HOTBAR_5("Hotbar Slot 5", "5", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_5),
    HOTBAR_6("Hotbar Slot 6", "6", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_6),
    HOTBAR_7("Hotbar Slot 7", "7", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_7),
    HOTBAR_8("Hotbar Slot 8", "8", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_8),
    HOTBAR_9("Hotbar Slot 9", "9", ControlCategory.HOTBAR, MinecraftKeyCodes.KEY_9),

    // OTHER
    SCREENSHOT("Screenshot", "F2", ControlCategory.OTHER, 291), // GLFW_KEY_F2
    DEBUG_F3("Debug Screen", "F3", ControlCategory.OTHER, MinecraftKeyCodes.KEY_F3),
    PERSPECTIVE_F5("Toggle Perspective", "F5", ControlCategory.OTHER, MinecraftKeyCodes.KEY_F5),
    CUSTOM_KEY("Custom Key", "KEY", ControlCategory.OTHER, MinecraftKeyCodes.KEY_UNKNOWN);

    companion object {
        fun fromName(name: String, fallback: ControlAction = JUMP): ControlAction {
            return entries.firstOrNull { it.name.equals(name, ignoreCase = true) } ?: fallback
        }
    }
}
