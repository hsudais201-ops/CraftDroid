package com.example.input

import org.json.JSONObject

data class ControlProfile(
    val id: String,
    val name: String,
    val isCustom: Boolean = false,
    val landscapeLayout: ControlLayout,
    val portraitLayout: ControlLayout
) {
    fun getLayout(orientation: LayoutOrientation): ControlLayout {
        return if (orientation == LayoutOrientation.LANDSCAPE) landscapeLayout else portraitLayout
    }

    fun updateLayout(layout: ControlLayout): ControlProfile {
        return if (layout.orientation == LayoutOrientation.LANDSCAPE) {
            copy(landscapeLayout = layout)
        } else {
            copy(portraitLayout = layout)
        }
    }

    fun toJson(): JSONObject {
        return JSONObject().apply {
            put("id", id)
            put("name", name)
            put("isCustom", isCustom)
            put("landscapeLayout", landscapeLayout.toJson())
            put("portraitLayout", portraitLayout.toJson())
        }
    }

    companion object {
        fun fromJson(json: JSONObject): ControlProfile {
            val id = json.optString("id", "profile_${System.currentTimeMillis()}")
            val name = json.optString("name", "Custom Layout")
            val isCustom = json.optBoolean("isCustom", true)

            val landJson = json.optJSONObject("landscapeLayout") ?: JSONObject()
            val portJson = json.optJSONObject("portraitLayout") ?: JSONObject()

            val landscape = ControlLayout.fromJson(landJson, LayoutOrientation.LANDSCAPE)
            val portrait = ControlLayout.fromJson(portJson, LayoutOrientation.PORTRAIT)

            return ControlProfile(
                id = id,
                name = name,
                isCustom = isCustom,
                landscapeLayout = landscape,
                portraitLayout = portrait
            )
        }

        fun createDefaultProfile(): ControlProfile {
            return ControlProfile(
                id = "default",
                name = "Default",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, createDefaultControls(LayoutOrientation.LANDSCAPE)),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, createDefaultControls(LayoutOrientation.PORTRAIT))
            )
        }

        fun createPvpProfile(): ControlProfile {
            val landscape = createDefaultControls(LayoutOrientation.LANDSCAPE).map { ctrl ->
                when (ctrl.action) {
                    ControlAction.ATTACK -> ctrl.copy(sizeScale = 1.35f, xPercent = 0.88f, yPercent = 0.50f)
                    ControlAction.JUMP -> ctrl.copy(sizeScale = 1.30f, xPercent = 0.88f, yPercent = 0.72f)
                    ControlAction.SPRINT -> ctrl.copy(sizeScale = 1.15f, xPercent = 0.12f, yPercent = 0.38f)
                    ControlAction.INVENTORY -> ctrl.copy(visible = false) // PvP: inventory hidden during battle
                    ControlAction.DROP -> ctrl.copy(xPercent = 0.12f, yPercent = 0.52f, sizeScale = 1.1f)
                    ControlAction.USE -> ctrl.copy(sizeScale = 1.20f, xPercent = 0.75f, yPercent = 0.50f)
                    else -> ctrl
                }
            }
            val portrait = createDefaultControls(LayoutOrientation.PORTRAIT).map { ctrl ->
                when (ctrl.action) {
                    ControlAction.ATTACK -> ctrl.copy(sizeScale = 1.3f)
                    ControlAction.JUMP -> ctrl.copy(sizeScale = 1.3f)
                    ControlAction.INVENTORY -> ctrl.copy(visible = false)
                    else -> ctrl
                }
            }
            return ControlProfile(
                id = "pvp",
                name = "PvP",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, landscape),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, portrait)
            )
        }

        fun createSurvivalProfile(): ControlProfile {
            val landscape = createDefaultControls(LayoutOrientation.LANDSCAPE).map { ctrl ->
                when (ctrl.action) {
                    ControlAction.INVENTORY -> ctrl.copy(visible = true, sizeScale = 1.15f, xPercent = 0.50f, yPercent = 0.82f)
                    ControlAction.SNEAK -> ctrl.copy(sizeScale = 1.1f, xPercent = 0.76f, yPercent = 0.72f)
                    else -> ctrl
                }
            }
            return ControlProfile(
                id = "survival",
                name = "Survival",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, landscape),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, createDefaultControls(LayoutOrientation.PORTRAIT))
            )
        }

        fun createBuildingProfile(): ControlProfile {
            val landscape = createDefaultControls(LayoutOrientation.LANDSCAPE).map { ctrl ->
                when (ctrl.action) {
                    ControlAction.USE -> ctrl.copy(name = "Place Block", sizeScale = 1.4f, xPercent = 0.75f, yPercent = 0.50f)
                    ControlAction.SNEAK -> ctrl.copy(name = "Sneak (Edge)", sizeScale = 1.2f, xPercent = 0.76f, yPercent = 0.72f)
                    else -> ctrl
                }
            }
            return ControlProfile(
                id = "building",
                name = "Building",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, landscape),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, createDefaultControls(LayoutOrientation.PORTRAIT))
            )
        }

        fun createTabletProfile(): ControlProfile {
            val landscape = createDefaultControls(LayoutOrientation.LANDSCAPE).map { ctrl ->
                ctrl.copy(
                    sizeScale = (ctrl.sizeScale * 1.15f).coerceIn(0.5f, 2.0f),
                    xPercent = if (ctrl.xPercent > 0.5f) (ctrl.xPercent * 1.03f).coerceAtMost(0.96f)
                               else (ctrl.xPercent * 0.95f).coerceAtLeast(0.04f)
                )
            }
            return ControlProfile(
                id = "tablet",
                name = "Tablet",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, landscape),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, createDefaultControls(LayoutOrientation.PORTRAIT))
            )
        }

        fun createControllerProfile(): ControlProfile {
            // Minimalist touch overlay designed to complement physical gamepads
            val landscape = createDefaultControls(LayoutOrientation.LANDSCAPE).map { ctrl ->
                when (ctrl.action) {
                    ControlAction.DEBUG_F3, ControlAction.CHAT, ControlAction.PAUSE, ControlAction.PERSPECTIVE_F5 ->
                        ctrl.copy(visible = true, opacity = 0.6f)
                    ControlAction.JOYSTICK_MOVE, ControlAction.CAMERA_LOOK ->
                        ctrl.copy(visible = false) // Handled by physical gamepad sticks
                    else -> ctrl.copy(opacity = 0.35f, sizeScale = 0.85f)
                }
            }
            return ControlProfile(
                id = "controller",
                name = "Controller",
                isCustom = false,
                landscapeLayout = ControlLayout(LayoutOrientation.LANDSCAPE, landscape),
                portraitLayout = ControlLayout(LayoutOrientation.PORTRAIT, createDefaultControls(LayoutOrientation.PORTRAIT))
            )
        }

        private fun createDefaultControls(orientation: LayoutOrientation): List<TouchControl> {
            val isLand = orientation == LayoutOrientation.LANDSCAPE
            val list = mutableListOf<TouchControl>()

            // 1. Camera Look Area (Large transparent center-right touchpad)
            list.add(
                TouchControl(
                    id = "area_camera",
                    name = "Camera / Look Area",
                    type = ControlType.TOUCH_AREA,
                    action = ControlAction.CAMERA_LOOK,
                    xPercent = if (isLand) 0.62f else 0.50f,
                    yPercent = if (isLand) 0.45f else 0.35f,
                    widthDp = if (isLand) 360 else 320,
                    heightDp = if (isLand) 240 else 260,
                    opacity = 0.05f,
                    shape = ButtonShape.TRANSPARENT,
                    hasBorder = false,
                    hasShadow = false
                )
            )

            // 2. Movement Joystick
            list.add(
                TouchControl(
                    id = "joy_movement",
                    name = "Movement Joystick",
                    type = ControlType.JOYSTICK,
                    action = ControlAction.JOYSTICK_MOVE,
                    xPercent = if (isLand) 0.14f else 0.22f,
                    yPercent = if (isLand) 0.72f else 0.78f,
                    widthDp = 130,
                    heightDp = 130,
                    opacity = 0.75f,
                    shape = ButtonShape.CIRCLE,
                    joystickMaxRadiusDp = 60f
                )
            )

            // Independent D-PAD / Movement Buttons (Forward, Backward, Left, Right)
            // Available as separate independent controls (hidden by default since joystick is on, but can be enabled/customized!)
            list.add(
                TouchControl(
                    id = "btn_forward",
                    name = "Forward (W)",
                    type = ControlType.BUTTON,
                    action = ControlAction.FORWARD,
                    xPercent = if (isLand) 0.14f else 0.22f,
                    yPercent = if (isLand) 0.54f else 0.64f,
                    widthDp = 48,
                    heightDp = 48,
                    opacity = 0.75f,
                    visible = false,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_backward",
                    name = "Backward (S)",
                    type = ControlType.BUTTON,
                    action = ControlAction.BACKWARD,
                    xPercent = if (isLand) 0.14f else 0.22f,
                    yPercent = if (isLand) 0.90f else 0.92f,
                    widthDp = 48,
                    heightDp = 48,
                    opacity = 0.75f,
                    visible = false,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_left",
                    name = "Left (A)",
                    type = ControlType.BUTTON,
                    action = ControlAction.LEFT,
                    xPercent = if (isLand) 0.05f else 0.08f,
                    yPercent = if (isLand) 0.72f else 0.78f,
                    widthDp = 48,
                    heightDp = 48,
                    opacity = 0.75f,
                    visible = false,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_right",
                    name = "Right (D)",
                    type = ControlType.BUTTON,
                    action = ControlAction.RIGHT,
                    xPercent = if (isLand) 0.23f else 0.36f,
                    yPercent = if (isLand) 0.72f else 0.78f,
                    widthDp = 48,
                    heightDp = 48,
                    opacity = 0.75f,
                    visible = false,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )

            // 3. Actions: Jump, Sneak, Sprint, Attack, Use, Drop, Inventory
            list.add(
                TouchControl(
                    id = "btn_jump",
                    name = "Jump",
                    type = ControlType.BUTTON,
                    action = ControlAction.JUMP,
                    xPercent = if (isLand) 0.88f else 0.84f,
                    yPercent = if (isLand) 0.72f else 0.78f,
                    widthDp = 64,
                    heightDp = 64,
                    opacity = 0.85f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_sneak",
                    name = "Sneak",
                    type = ControlType.BUTTON,
                    action = ControlAction.SNEAK,
                    xPercent = if (isLand) 0.76f else 0.68f,
                    yPercent = if (isLand) 0.72f else 0.78f,
                    widthDp = 54,
                    heightDp = 54,
                    opacity = 0.80f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_sprint",
                    name = "Sprint",
                    type = ControlType.BUTTON,
                    action = ControlAction.SPRINT,
                    xPercent = if (isLand) 0.12f else 0.14f,
                    yPercent = if (isLand) 0.40f else 0.58f,
                    widthDp = 52,
                    heightDp = 52,
                    opacity = 0.80f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_attack",
                    name = "Attack",
                    type = ControlType.BUTTON,
                    action = ControlAction.ATTACK,
                    xPercent = if (isLand) 0.88f else 0.84f,
                    yPercent = if (isLand) 0.52f else 0.62f,
                    widthDp = 60,
                    heightDp = 60,
                    opacity = 0.85f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_use",
                    name = "Use item",
                    type = ControlType.BUTTON,
                    action = ControlAction.USE,
                    xPercent = if (isLand) 0.76f else 0.68f,
                    yPercent = if (isLand) 0.52f else 0.62f,
                    widthDp = 58,
                    heightDp = 58,
                    opacity = 0.85f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_drop",
                    name = "Drop",
                    type = ControlType.BUTTON,
                    action = ControlAction.DROP,
                    xPercent = if (isLand) 0.12f else 0.14f,
                    yPercent = if (isLand) 0.52f else 0.68f,
                    widthDp = 50,
                    heightDp = 50,
                    opacity = 0.75f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )
            list.add(
                TouchControl(
                    id = "btn_inventory",
                    name = "Inventory",
                    type = ControlType.BUTTON,
                    action = ControlAction.INVENTORY,
                    xPercent = if (isLand) 0.50f else 0.50f,
                    yPercent = if (isLand) 0.86f else 0.88f,
                    widthDp = 52,
                    heightDp = 52,
                    opacity = 0.80f,
                    shape = ButtonShape.MINECRAFT_STYLE
                )
            )

            // 4. Hotbar Slots 1..9
            val hotbarY = if (isLand) 0.95f else 0.96f
            val hotbarStartX = if (isLand) 0.28f else 0.08f
            val hotbarSpacing = if (isLand) 0.055f else 0.105f
            val hotbarActions = listOf(
                ControlAction.HOTBAR_1, ControlAction.HOTBAR_2, ControlAction.HOTBAR_3,
                ControlAction.HOTBAR_4, ControlAction.HOTBAR_5, ControlAction.HOTBAR_6,
                ControlAction.HOTBAR_7, ControlAction.HOTBAR_8, ControlAction.HOTBAR_9
            )
            hotbarActions.forEachIndexed { index, act ->
                list.add(
                    TouchControl(
                        id = "btn_hotbar_${index + 1}",
                        name = "Slot ${index + 1}",
                        type = ControlType.HOTBAR_SLOT,
                        action = act,
                        xPercent = (hotbarStartX + index * hotbarSpacing).coerceIn(0.04f, 0.96f),
                        yPercent = hotbarY,
                        widthDp = 42,
                        heightDp = 42,
                        opacity = 0.80f,
                        shape = ButtonShape.SQUARE
                    )
                )
            }

            // 5. System & Navigation: Pause, F3, F5, Chat, Screenshot
            list.add(
                TouchControl(
                    id = "btn_pause",
                    name = "Pause (Esc)",
                    type = ControlType.BUTTON,
                    action = ControlAction.PAUSE,
                    xPercent = if (isLand) 0.06f else 0.10f,
                    yPercent = 0.07f,
                    widthDp = 46,
                    heightDp = 38,
                    opacity = 0.80f,
                    shape = ButtonShape.ROUNDED
                )
            )
            list.add(
                TouchControl(
                    id = "btn_f3",
                    name = "F3 (Debug)",
                    type = ControlType.BUTTON,
                    action = ControlAction.DEBUG_F3,
                    xPercent = if (isLand) 0.45f else 0.35f,
                    yPercent = 0.07f,
                    widthDp = 46,
                    heightDp = 38,
                    opacity = 0.75f,
                    shape = ButtonShape.ROUNDED
                )
            )
            list.add(
                TouchControl(
                    id = "btn_f5",
                    name = "Toggle Perspective (F5)",
                    type = ControlType.BUTTON,
                    action = ControlAction.PERSPECTIVE_F5,
                    xPercent = if (isLand) 0.35f else 0.55f,
                    yPercent = 0.07f,
                    widthDp = 46,
                    heightDp = 38,
                    opacity = 0.75f,
                    shape = ButtonShape.ROUNDED
                )
            )
            list.add(
                TouchControl(
                    id = "btn_chat",
                    name = "Chat",
                    type = ControlType.BUTTON,
                    action = ControlAction.CHAT,
                    xPercent = if (isLand) 0.65f else 0.75f,
                    yPercent = 0.07f,
                    widthDp = 48,
                    heightDp = 38,
                    opacity = 0.75f,
                    shape = ButtonShape.ROUNDED
                )
            )
            list.add(
                TouchControl(
                    id = "btn_screenshot",
                    name = "Screenshot (F2)",
                    type = ControlType.BUTTON,
                    action = ControlAction.SCREENSHOT,
                    xPercent = if (isLand) 0.55f else 0.88f,
                    yPercent = 0.07f,
                    widthDp = 46,
                    heightDp = 38,
                    opacity = 0.70f,
                    visible = false, // Hidden by default, can be toggled on
                    shape = ButtonShape.ROUNDED
                )
            )

            return list
        }
    }
}
