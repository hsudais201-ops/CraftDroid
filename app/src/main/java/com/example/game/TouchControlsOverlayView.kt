package com.example.game

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.LinearGradient
import android.graphics.Shader
import android.os.Build
import android.view.MotionEvent
import android.view.HapticFeedbackConstants
import android.view.View
import android.view.WindowInsets
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import androidx.lifecycle.Lifecycle
import kotlinx.coroutines.launch
import kotlin.math.max
import com.example.input.ButtonShape
import com.example.input.ControlType
import com.example.input.TouchControl
import com.example.input.TouchInputManager

/**
 * Runtime touch-control layer drawn above the real Minecraft SurfaceView.
 * It consumes touches only for configured controls; look-area/empty touches are
 * forwarded to the shared physical-touch path.
 */
class TouchControlsOverlayView(
    context: Context,
    private val touchManager: TouchInputManager
) : View(context) {

    private var density = resources.displayMetrics.density
    private var insetLeft = 0f
    private var insetTop = 0f
    private var insetRight = 0f
    private var insetBottom = 0f
    private val fillPaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val strokePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = 2f * density
    }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        textAlign = Paint.Align.CENTER
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }

    private data class ActivePointer(val kind: Kind, val control: TouchControl? = null)
    private enum class Kind { CONTROL, JOYSTICK, CAMERA }

    private val activePointers = HashMap<Int, ActivePointer>()
    private var joystickPointerId: Int? = null
    private var joystickOriginX = 0f
    private var joystickOriginY = 0f

    init {
        setWillNotDraw(false)
        isClickable = true
        isFocusable = false
        (context as? LifecycleOwner)?.lifecycleScope?.launch {
            (context as LifecycleOwner).repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch { touchManager.currentLayout.collect { invalidate() } }
                launch { touchManager.orientation.collect { invalidate() } }
                launch { touchManager.pressedControlIds.collect { invalidate() } }
            }
        }

                setOnApplyWindowInsetsListener { _, insets ->
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                val bars = insets.getInsets(
                    WindowInsets.Type.statusBars() or
                        WindowInsets.Type.navigationBars() or
                        WindowInsets.Type.displayCutout()
                )
                insetLeft = bars.left.toFloat()
                insetTop = bars.top.toFloat()
                insetRight = bars.right.toFloat()
                insetBottom = bars.bottom.toFloat()
            } else {
                insetLeft = insets.systemWindowInsetLeft.toFloat()
                insetTop = insets.systemWindowInsetTop.toFloat()
                insetRight = insets.systemWindowInsetRight.toFloat()
                insetBottom = insets.systemWindowInsetBottom.toFloat()
            }
            invalidate()
            insets
        }
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        density = resources.displayMetrics.density
        touchManager.setOrientation(
            if (w >= h) com.example.input.LayoutOrientation.LANDSCAPE
            else com.example.input.LayoutOrientation.PORTRAIT
        )
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val layout = touchManager.currentLayout.value
        layout.controls.forEach { control ->
            if (!control.visible || control.type == ControlType.TOUCH_AREA) return@forEach
            val bounds = controlBounds(control)
            val pressed = touchManager.pressedControlIds.value.contains(control.id)
            val alpha = ((control.opacity + if (pressed) 0.16f else 0f).coerceIn(0f, 1f) * 255f).toInt()

            if (control.type == ControlType.JOYSTICK) {
                drawPremiumJoystick(canvas, bounds, control, alpha)
            } else {
                drawPremiumButton(canvas, bounds, control, pressed, alpha)
            }
        }
    }

    private fun drawPremiumButton(
        canvas: Canvas,
        bounds: RectF,
        control: TouchControl,
        pressed: Boolean,
        alpha: Int
    ) {
        val radius = (control.cornerRadiusDp * density).coerceAtLeast(6f)
        val shape = control.shape

        // Subtle outer glow gives controls depth without using an expensive shadow layer.
        if (control.hasShadow && alpha > 8) {
            fillPaint.shader = null
            fillPaint.style = Paint.Style.FILL
            fillPaint.color = Color.BLACK
            fillPaint.alpha = (alpha * 0.28f).toInt()
            val shadow = RectF(bounds).apply { offset(0f, 2.5f * density) }
            when (shape) {
                ButtonShape.CIRCLE -> canvas.drawOval(shadow, fillPaint)
                ButtonShape.SQUARE -> canvas.drawRect(shadow, fillPaint)
                else -> canvas.drawRoundRect(shadow, radius, radius, fillPaint)
            }
        }

        val top = if (pressed) Color.rgb(92, 132, 145) else Color.rgb(58, 82, 94)
        val bottom = if (pressed) Color.rgb(54, 104, 90) else Color.rgb(29, 48, 57)
        fillPaint.style = Paint.Style.FILL
        fillPaint.shader = LinearGradient(
            bounds.left, bounds.top, bounds.left, bounds.bottom,
            top, bottom, Shader.TileMode.CLAMP
        )
        fillPaint.alpha = alpha
        when (shape) {
            ButtonShape.CIRCLE -> canvas.drawOval(bounds, fillPaint)
            ButtonShape.SQUARE -> canvas.drawRect(bounds, fillPaint)
            ButtonShape.TRANSPARENT -> {
                fillPaint.alpha = (alpha * 0.12f).toInt()
                canvas.drawRoundRect(bounds, radius, radius, fillPaint)
            }
            ButtonShape.MINIMAL -> {
                fillPaint.alpha = (alpha * 0.38f).toInt()
                canvas.drawRoundRect(bounds, radius, radius, fillPaint)
            }
            else -> canvas.drawRoundRect(bounds, radius, radius, fillPaint)
        }
        fillPaint.shader = null

        if (control.hasBorder && shape != ButtonShape.TRANSPARENT) {
            strokePaint.style = Paint.Style.STROKE
            strokePaint.strokeWidth = (1.25f * density).coerceAtLeast(1f)
            strokePaint.color = Color.WHITE
            strokePaint.alpha = (alpha * if (pressed) 0.62f else 0.25f).toInt()
            when (shape) {
                ButtonShape.CIRCLE -> canvas.drawOval(bounds, strokePaint)
                ButtonShape.SQUARE -> canvas.drawRect(bounds, strokePaint)
                else -> canvas.drawRoundRect(bounds, radius, radius, strokePaint)
            }
        }

        // Top-edge highlight makes the button read like a glass/metal control.
        if (shape != ButtonShape.TRANSPARENT) {
            strokePaint.strokeWidth = (1f * density).coerceAtLeast(1f)
            strokePaint.color = Color.WHITE
            strokePaint.alpha = (alpha * 0.12f).toInt()
            val highlight = RectF(bounds).apply { inset(1.5f * density, 1.5f * density) }
            canvas.drawRoundRect(highlight, radius, radius, strokePaint)
        }

        textPaint.color = Color.WHITE
        textPaint.alpha = alpha.coerceAtLeast(100)
        textPaint.textSize = when {
            control.displayLabel.length >= 7 -> 11f * density
            control.displayLabel.length >= 5 -> 12f * density
            else -> 14f * density
        }
        textPaint.typeface = android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD)
        canvas.drawText(
            control.displayLabel,
            bounds.centerX(),
            bounds.centerY() - (textPaint.ascent() + textPaint.descent()) / 2f,
            textPaint
        )
    }

    private fun drawPremiumJoystick(canvas: Canvas, bounds: RectF, control: TouchControl, alpha: Int) {
        val cx = bounds.centerX()
        val cy = bounds.centerY()
        val outer = minOf(bounds.width(), bounds.height()) / 2f
        val active = touchManager.isJoystickActive

        // Layered thumbstick: outer glass ring, inner track, then a physical-looking knob.
        fillPaint.style = Paint.Style.FILL
        fillPaint.shader = LinearGradient(
            bounds.left, bounds.top, bounds.right, bounds.bottom,
            Color.rgb(54, 77, 87), Color.rgb(24, 39, 47), Shader.TileMode.CLAMP
        )
        fillPaint.alpha = alpha
        canvas.drawCircle(cx, cy, outer, fillPaint)
        fillPaint.shader = null

        strokePaint.style = Paint.Style.STROKE
        strokePaint.strokeWidth = 2f * density
        strokePaint.color = Color.WHITE
        strokePaint.alpha = (alpha * 0.22f).toInt()
        canvas.drawCircle(cx, cy, outer - 2f * density, strokePaint)
        strokePaint.strokeWidth = 1f * density
        strokePaint.alpha = (alpha * 0.12f).toInt()
        canvas.drawCircle(cx, cy, outer * 0.68f, strokePaint)

        val maxRadius = (control.joystickMaxRadiusDp * density).coerceAtMost(outer * 0.72f)
        val originX = if (active && control.joystickDynamicOrigin) joystickOriginX else cx
        val originY = if (active && control.joystickDynamicOrigin) joystickOriginY else cy
        val dx = touchManager.joystickDeltaX * maxRadius
        val dy = touchManager.joystickDeltaY * maxRadius
        val knobRadius = outer * 0.34f
        val kx = originX + dx
        val ky = originY + dy

        if (active && control.joystickDynamicOrigin) {
            strokePaint.color = Color.WHITE
            strokePaint.alpha = (alpha * 0.20f).toInt()
            strokePaint.strokeWidth = 1f * density
            canvas.drawCircle(originX, originY, outer * 0.48f, strokePaint)
        }

        fillPaint.color = if (active) Color.rgb(86, 177, 145) else Color.rgb(67, 103, 112)
        fillPaint.alpha = alpha
        canvas.drawCircle(kx, ky, knobRadius, fillPaint)
        strokePaint.color = Color.WHITE
        strokePaint.alpha = (alpha * if (active) 0.45f else 0.20f).toInt()
        strokePaint.strokeWidth = 1.5f * density
        canvas.drawCircle(kx, ky, knobRadius - density, strokePaint)

        textPaint.color = Color.WHITE
        textPaint.alpha = (alpha * 0.85f).toInt()
        textPaint.textSize = 11f * density
        textPaint.typeface = android.graphics.Typeface.create("sans-serif", android.graphics.Typeface.BOLD)
        canvas.drawText("MOVE", cx, cy - (textPaint.ascent() + textPaint.descent()) / 2f, textPaint)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (width <= 0 || height <= 0) return true
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val index = event.actionIndex
                val pointerId = event.getPointerId(index)
                val x = event.getX(index)
                val y = event.getY(index)
                val control = hitTest(x, y)
                when {
                    control?.type == ControlType.JOYSTICK && joystickPointerId == null -> {
                        activePointers[pointerId] = ActivePointer(Kind.JOYSTICK, control)
                        joystickPointerId = pointerId
                        if (control.joystickDynamicOrigin) {
                            val bounds = controlBounds(control)
                            val maxOriginOffset = minOf(bounds.width(), bounds.height()) * 0.28f
                            joystickOriginX = x.coerceIn(bounds.centerX() - maxOriginOffset, bounds.centerX() + maxOriginOffset)
                            joystickOriginY = y.coerceIn(bounds.centerY() - maxOriginOffset, bounds.centerY() + maxOriginOffset)
                        } else {
                            joystickOriginX = controlBounds(control).centerX()
                            joystickOriginY = controlBounds(control).centerY()
                        }
                        updateJoystick(control, x, y)
                        performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                    }
                    control?.type == ControlType.TOUCH_AREA -> {
                        activePointers[pointerId] = ActivePointer(Kind.CAMERA, control)
                        touchManager.onPhysicalTouchDown(pointerId, x, y)
                        cameraLastPositions[pointerId] = x to y
                    }
                    control != null -> {
                        activePointers[pointerId] = ActivePointer(Kind.CONTROL, control)
                        val token = touchManager.allocatePointerToken()
                        touchManager.onControlPointerDown(control, token)
                        controlPointerTokens[pointerId] = token
                        performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                    }
                    else -> {
                        activePointers[pointerId] = ActivePointer(Kind.CAMERA, null)
                        touchManager.onPhysicalTouchDown(pointerId, x, y)
                        cameraLastPositions[pointerId] = x to y
                    }
                }
                invalidate()
            }

            MotionEvent.ACTION_MOVE -> {
                for (index in 0 until event.pointerCount) {
                    val pointerId = event.getPointerId(index)
                    val active = activePointers[pointerId] ?: continue
                    val x = event.getX(index)
                    val y = event.getY(index)
                    when (active.kind) {
                        Kind.JOYSTICK -> updateJoystick(active.control ?: continue, x, y)
                        Kind.CAMERA -> {
                            val control = active.control
                            if (control != null && control.type == ControlType.TOUCH_AREA) {
                                val last = cameraLastPositions[pointerId]
                                if (last != null) {
                                    touchManager.onCameraLook(
                                        x - last.first,
                                        y - last.second,
                                        control.cameraSensitivity,
                                        control.cameraInvertY,
                                        control.cameraHorizontalSens,
                                        control.cameraVerticalSens
                                    )
                                }
                                cameraLastPositions[pointerId] = x to y
                            } else {
                                val last = cameraLastPositions[pointerId]
                                if (last != null) {
                                    touchManager.onPhysicalTouchMove(pointerId, x, y, x - last.first, y - last.second)
                                }
                                cameraLastPositions[pointerId] = x to y
                            }
                        }
                        Kind.CONTROL -> Unit
                    }
                }
                invalidate()
            }

            MotionEvent.ACTION_POINTER_UP, MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                val cancel = event.actionMasked == MotionEvent.ACTION_CANCEL
                if (cancel) {
                    releaseAllTouches()
                } else {
                    val index = event.actionIndex.coerceIn(0, event.pointerCount - 1)
                    val pointerId = event.getPointerId(index)
                    releasePointer(pointerId, event.getX(index), event.getY(index))
                }
                invalidate()
            }
        }
        return true
    }

    private val controlPointerTokens = HashMap<Int, Int>()
    private val cameraLastPositions = HashMap<Int, Pair<Float, Float>>()

    private fun releasePointer(pointerId: Int, x: Float, y: Float) {
        when (activePointers.remove(pointerId)?.kind) {
            Kind.CONTROL -> controlPointerTokens.remove(pointerId)?.let { touchManager.onControlPointerUp(it) }
            Kind.JOYSTICK -> {
                if (joystickPointerId == pointerId) {
                    joystickPointerId = null
                    joystickOriginX = 0f
                    joystickOriginY = 0f
                }
                touchManager.onJoystickRelease()
            }
            Kind.CAMERA -> touchManager.onPhysicalTouchUp(pointerId, x, y)
            null -> Unit
        }
        cameraLastPositions.remove(pointerId)
    }

    fun releaseAllTouches() {
        activePointers.keys.toList().forEach { id -> releasePointer(id, 0f, 0f) }
        activePointers.clear()
        controlPointerTokens.clear()
        cameraLastPositions.clear()
        joystickPointerId = null
        joystickOriginX = 0f
        joystickOriginY = 0f
        touchManager.releaseAllInputs()
    }

    private fun updateJoystick(control: TouchControl, x: Float, y: Float) {
        val bounds = controlBounds(control)
        val originX = if (control.joystickDynamicOrigin && joystickPointerId != null) joystickOriginX else bounds.centerX()
        val originY = if (control.joystickDynamicOrigin && joystickPointerId != null) joystickOriginY else bounds.centerY()
        val dx = x - originX
        val dy = y - originY
        val maxRadius = control.joystickMaxRadiusDp * density
        touchManager.onJoystickMove(dx, dy, maxRadius, control.joystickDeadZone)
    }

    private fun hitTest(x: Float, y: Float): TouchControl? {
        // Highest z-order is the end of the persisted list, so test from front to back.
        val controls = touchManager.currentLayout.value.controls.asReversed()
        return controls.firstOrNull { control ->
            if (!control.visible) return@firstOrNull false
            controlBounds(control).contains(x, y)
        }
    }

    private fun controlBounds(control: TouchControl): RectF {
        val w = control.effectiveWidthDp * density
        val h = control.effectiveHeightDp * density
        val safeLeft = insetLeft
        val safeTop = insetTop
        val safeRight = max(safeLeft + 1f, width - insetRight)
        val safeBottom = max(safeTop + 1f, height - insetBottom)
        val safeWidth = max(1f, safeRight - safeLeft)
        val safeHeight = max(1f, safeBottom - safeTop)
        val rawCx = safeLeft + safeWidth * control.xPercent
        val rawCy = safeTop + safeHeight * control.yPercent
        val halfW = w / 2f
        val halfH = h / 2f
        val cx = rawCx.coerceIn(safeLeft + halfW, safeRight - halfW)
        val cy = rawCy.coerceIn(safeTop + halfH, safeBottom - halfH)
        return RectF(cx - halfW, cy - halfH, cx + halfW, cy + halfH)
    }
}
