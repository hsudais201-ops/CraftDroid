package com.example.game

import android.content.Context
import android.graphics.Color
import android.view.InputDevice
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.Surface
import android.view.SurfaceHolder
import android.view.SurfaceView
import com.example.input.InputBridge
import com.example.input.TouchInputManager
import com.example.logs.LauncherLogger
import kotlin.math.abs

/** Android host surface for Minecraft. Touch, keyboard and physical controllers are routed to JNI. */
class GameSurfaceView(
    context: Context,
    private val input: InputBridge,
    private val callbacks: Callbacks,
    private val touchManager: TouchInputManager? = null
) : SurfaceView(context), SurfaceHolder.Callback {

    interface Callbacks {
        fun onSurfaceReady(surface: Surface, width: Int, height: Int)
        fun onSurfaceDestroyed()
    }

    private var lastX = 0f
    private var lastY = 0f
    private var primaryTouchPointerId: Int? = null

    init {
        holder.addCallback(this)
        setBackgroundColor(Color.BLACK)
        isFocusable = true
        isFocusableInTouchMode = true
        keepScreenOn = true
        setOnGenericMotionListener { _, event -> handleGenericMotion(event) }
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        requestFocus()
        callbacks.onSurfaceReady(holder.surface, width, height)
        LauncherLogger.info("Game surface created: ${width}x${height}")
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        callbacks.onSurfaceReady(holder.surface, width, height)
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        callbacks.onSurfaceDestroyed()
        input.releaseAll()
        LauncherLogger.info("Game surface destroyed")
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        val index = event.actionIndex.coerceIn(0, event.pointerCount - 1)
        val pointerId = event.getPointerId(index)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                primaryTouchPointerId = pointerId
                val x = event.getX(index)
                val y = event.getY(index)
                touchManager?.onPhysicalTouchDown(pointerId, x, y)
                lastX = x
                lastY = y
                input.mouse.setCursorPosition(x, y)
            }
            MotionEvent.ACTION_POINTER_DOWN -> {
                val x = event.getX(index)
                val y = event.getY(index)
                touchManager?.onPhysicalTouchDown(pointerId, x, y)
            }
            MotionEvent.ACTION_MOVE -> {
                val primaryId = primaryTouchPointerId
                if (primaryId != null) {
                    val primaryIndex = (0 until event.pointerCount).firstOrNull { event.getPointerId(it) == primaryId }
                    if (primaryIndex != null) {
                        val x = event.getX(primaryIndex)
                        val y = event.getY(primaryIndex)
                        val dx = x - lastX
                        val dy = y - lastY
                        touchManager?.onPhysicalTouchMove(primaryId, x, y, dx, dy)
                        if (touchManager == null && (abs(dx) > 0.01f || abs(dy) > 0.01f)) {
                            input.mouse.setCursorPosition(x, y)
                            input.mouse.sendMouseMove(dx, dy)
                        }
                        lastX = x
                        lastY = y
                    }
                }
            }
            MotionEvent.ACTION_POINTER_UP -> {
                val x = event.getX(index)
                val y = event.getY(index)
                touchManager?.onPhysicalTouchUp(pointerId, x, y)
                if (pointerId == primaryTouchPointerId) {
                    val remaining = (0 until event.pointerCount).filter { it != index }
                    val replacementIndex = remaining.firstOrNull()
                    primaryTouchPointerId = replacementIndex?.let { event.getPointerId(it) }
                    replacementIndex?.let {
                        lastX = event.getX(it)
                        lastY = event.getY(it)
                        input.mouse.setCursorPosition(lastX, lastY)
                    }
                }
            }
            MotionEvent.ACTION_UP -> {
                val ids = (0 until event.pointerCount).map { event.getPointerId(it) }
                ids.forEach { id ->
                    val pointerIndex = (0 until event.pointerCount).firstOrNull { event.getPointerId(it) == id }
                    if (pointerIndex != null) {
                        touchManager?.onPhysicalTouchUp(id, event.getX(pointerIndex), event.getY(pointerIndex))
                    }
                }
                primaryTouchPointerId = null
                input.mouse.setCursorPosition(event.x, event.y)
            }
            MotionEvent.ACTION_CANCEL -> {
                touchManager?.releaseAllPhysicalTouches()
                primaryTouchPointerId = null
                lastX = 0f
                lastY = 0f
                // Cancellation is not a real pointer position; do not synthesize
                // a cursor move from event.x/event.y.
            }
            MotionEvent.ACTION_SCROLL -> {
                val scroll = event.getAxisValue(MotionEvent.AXIS_VSCROLL)
                val horizontal = event.getAxisValue(MotionEvent.AXIS_HSCROLL)
                if (scroll != 0f || horizontal != 0f) input.mouse.sendMouseScroll(scroll, horizontal)
            }
        }
        return true
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if ((event.source and InputDevice.SOURCE_GAMEPAD) != 0 || (event.source and InputDevice.SOURCE_JOYSTICK) != 0) {
            val button = gamepadButtonIndex(keyCode)
            if (button >= 0) { input.gamepad.sendButton(button, true); return true }
        }
        if (event.action == KeyEvent.ACTION_DOWN && event.unicodeChar != 0 && (event.unicodeChar and KeyEvent.META_ALT_MASK) == 0) {
            // Unicode text is handled by Android key events; the native bridge exposes key events only.
        }
        val mc = inputKey(keyCode)
        if (mc != -1) {
            input.keyboard.sendKeyEventWithModifiers(mc, true, modifiers(event))
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if ((event.source and InputDevice.SOURCE_GAMEPAD) != 0 || (event.source and InputDevice.SOURCE_JOYSTICK) != 0) {
            val button = gamepadButtonIndex(keyCode)
            if (button >= 0) { input.gamepad.sendButton(button, false); return true }
        }
        val mc = inputKey(keyCode)
        if (mc != -1) {
            input.keyboard.sendKeyEventWithModifiers(mc, false, modifiers(event))
            return true
        }
        return super.onKeyUp(keyCode, event)
    }

    private fun handleGenericMotion(event: MotionEvent): Boolean {
        if ((event.source and InputDevice.SOURCE_CLASS_JOYSTICK) == 0) return false
        val axes = intArrayOf(
            MotionEvent.AXIS_X, MotionEvent.AXIS_Y,
            MotionEvent.AXIS_Z, MotionEvent.AXIS_RZ,
            MotionEvent.AXIS_LTRIGGER, MotionEvent.AXIS_RTRIGGER
        )
        axes.forEachIndexed { index, axis ->
            input.gamepad.sendAxis(index, event.getAxisValue(axis).coerceIn(-1f, 1f))
        }
        return true
    }

    private fun modifiers(event: KeyEvent): Int {
        var mods = 0
        if (event.isShiftPressed) mods = mods or 0x0001
        if (event.isCtrlPressed) mods = mods or 0x0002
        if (event.isAltPressed) mods = mods or 0x0004
        if (event.isMetaPressed) mods = mods or 0x0008
        return mods
    }

    private fun gamepadButtonIndex(keyCode: Int): Int = when (keyCode) {
        KeyEvent.KEYCODE_BUTTON_A -> 0
        KeyEvent.KEYCODE_BUTTON_B -> 1
        KeyEvent.KEYCODE_BUTTON_X -> 2
        KeyEvent.KEYCODE_BUTTON_Y -> 3
        KeyEvent.KEYCODE_BUTTON_L1 -> 4
        KeyEvent.KEYCODE_BUTTON_R1 -> 5
        KeyEvent.KEYCODE_BUTTON_START -> 6
        KeyEvent.KEYCODE_BUTTON_SELECT -> 7
        KeyEvent.KEYCODE_BUTTON_THUMBL -> 8
        KeyEvent.KEYCODE_BUTTON_THUMBR -> 9
        else -> -1
    }

    private fun inputKey(keyCode: Int): Int = keyCode
}
