package com.example.input

import android.view.KeyEvent

class KeyboardManager {

    fun mapAndroidKeyToMinecraft(keyCode: Int): Int {
        return when (keyCode) {
            KeyEvent.KEYCODE_W -> MinecraftKeyCodes.KEY_W
            KeyEvent.KEYCODE_A -> MinecraftKeyCodes.KEY_A
            KeyEvent.KEYCODE_S -> MinecraftKeyCodes.KEY_S
            KeyEvent.KEYCODE_D -> MinecraftKeyCodes.KEY_D
            KeyEvent.KEYCODE_SPACE -> MinecraftKeyCodes.KEY_SPACE
            KeyEvent.KEYCODE_SHIFT_LEFT, KeyEvent.KEYCODE_SHIFT_RIGHT -> MinecraftKeyCodes.KEY_LEFT_SHIFT
            KeyEvent.KEYCODE_CTRL_LEFT, KeyEvent.KEYCODE_CTRL_RIGHT -> MinecraftKeyCodes.KEY_LEFT_CONTROL
            KeyEvent.KEYCODE_ALT_LEFT, KeyEvent.KEYCODE_ALT_RIGHT -> MinecraftKeyCodes.KEY_LEFT_ALT
            KeyEvent.KEYCODE_E -> MinecraftKeyCodes.KEY_E
            KeyEvent.KEYCODE_Q -> MinecraftKeyCodes.KEY_Q
            KeyEvent.KEYCODE_T -> MinecraftKeyCodes.KEY_T
            KeyEvent.KEYCODE_F -> MinecraftKeyCodes.KEY_F
            KeyEvent.KEYCODE_C -> MinecraftKeyCodes.KEY_C
            KeyEvent.KEYCODE_ESCAPE, KeyEvent.KEYCODE_BACK -> MinecraftKeyCodes.KEY_ESCAPE
            KeyEvent.KEYCODE_ENTER -> MinecraftKeyCodes.KEY_ENTER
            KeyEvent.KEYCODE_TAB -> MinecraftKeyCodes.KEY_TAB
            KeyEvent.KEYCODE_DEL -> MinecraftKeyCodes.KEY_BACKSPACE
            KeyEvent.KEYCODE_F3 -> MinecraftKeyCodes.KEY_F3
            KeyEvent.KEYCODE_F5 -> MinecraftKeyCodes.KEY_F5
            KeyEvent.KEYCODE_0 -> MinecraftKeyCodes.KEY_0
            KeyEvent.KEYCODE_1 -> MinecraftKeyCodes.KEY_1
            KeyEvent.KEYCODE_2 -> MinecraftKeyCodes.KEY_2
            KeyEvent.KEYCODE_3 -> MinecraftKeyCodes.KEY_3
            KeyEvent.KEYCODE_4 -> MinecraftKeyCodes.KEY_4
            KeyEvent.KEYCODE_5 -> MinecraftKeyCodes.KEY_5
            KeyEvent.KEYCODE_6 -> MinecraftKeyCodes.KEY_6
            KeyEvent.KEYCODE_7 -> MinecraftKeyCodes.KEY_7
            KeyEvent.KEYCODE_8 -> MinecraftKeyCodes.KEY_8
            KeyEvent.KEYCODE_9 -> MinecraftKeyCodes.KEY_9
            else -> MinecraftKeyCodes.KEY_UNKNOWN
        }
    }
}
