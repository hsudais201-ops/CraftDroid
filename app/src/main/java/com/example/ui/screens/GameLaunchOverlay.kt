package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.style.TextAlign
import com.example.input.ButtonShape
import com.example.input.ControlType
import com.example.input.TouchControl
import com.example.input.VirtualButtonType
import com.example.launcher.LaunchState
import com.example.logs.LauncherLogger
import com.example.logs.LogLevel
import com.example.ui.LauncherViewModel
import kotlin.math.roundToInt

@Composable
fun GameLaunchOverlay(
    viewModel: LauncherViewModel,
    launchState: LaunchState,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val touchManager = viewModel.container.touchInputManager
    val touchSettings by touchManager.settings.collectAsState()
    val virtualButtons by touchManager.buttons.collectAsState()
    val currentLayout by touchManager.currentLayout.collectAsState()
    val pressedControlIds by touchManager.pressedControlIds.collectAsState()
    val logs by viewModel.logs.collectAsState()
    val listState = rememberLazyListState()

    var showControlsOverlay by remember { mutableStateOf(true) }
    var showLogsDrawer by remember { mutableStateOf(false) }
    var isEditMode by remember { mutableStateOf(false) }

    when (launchState) {
        is LaunchState.Idle -> {
            // Nothing to show
        }

        is LaunchState.Preparing -> {
            // Step 1 through 6 animated sequence
            Box(
                modifier = modifier
                    .fillMaxSize()
                    .background(Color(0xFF0D1117).copy(alpha = 0.95f)),
                contentAlignment = Alignment.Center
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .padding(16.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(
                        modifier = Modifier.padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "LAUNCHING MINECRAFT",
                            style = MaterialTheme.typography.titleLarge.copy(
                                fontWeight = FontWeight.Black,
                                letterSpacing = 2.sp
                            ),
                            color = Color(0xFF81C784)
                        )
                        Spacer(modifier = Modifier.height(16.dp))

                        StepIndicator(1, "Checking account", launchState.currentStep)
                        StepIndicator(2, "Checking Minecraft files", launchState.currentStep)
                        StepIndicator(3, "Checking Java runtime", launchState.currentStep)
                        StepIndicator(4, "Loading libraries", launchState.currentStep)
                        StepIndicator(5, "Preparing renderer", launchState.currentStep)
                        StepIndicator(6, "Starting Minecraft", launchState.currentStep)

                        Spacer(modifier = Modifier.height(16.dp))
                        LinearProgressIndicator(
                            progress = { launchState.currentStep.toFloat() / 6f },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(6.dp)
                                .clip(RoundedCornerShape(3.dp))
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = launchState.details,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(16.dp))
                        OutlinedButton(onClick = { viewModel.container.launchManager.kill() }) {
                            Text("Abort Launch")
                        }
                    }
                }
            }
        }

        is LaunchState.Running -> {
            // Running State: Game canvas / Stream logs + Touch Controls Overlay
            BoxWithConstraints(
                modifier = modifier
                    .fillMaxSize()
                    .background(Color.Black)
            ) {
                val screenW = maxWidth.value
                val screenH = maxHeight.value

                // Background Game Log stream
                val gameLogs = remember(logs) { logs.takeLast(100) }
                LaunchedEffect(gameLogs.size) {
                    if (gameLogs.isNotEmpty()) listState.scrollToItem(gameLogs.size - 1)
                }

                LazyColumn(
                    state = listState,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(8.dp)
                ) {
                    items(gameLogs) { entry ->
                        Text(
                            text = entry.message,
                            color = if (entry.level == LogLevel.MINECRAFT) Color(0xFF81C784) else Color.LightGray,
                            fontFamily = FontFamily.Monospace,
                            fontSize = 11.sp,
                            lineHeight = 14.sp
                        )
                    }
                }

                // Top Floating Game Bar (Kill, Soft Keyboard, Show/Hide Controls, Logs)
                Row(
                    modifier = Modifier
                        .align(Alignment.TopCenter)
                        .padding(top = 16.dp)
                        .clip(RoundedCornerShape(20.dp))
                        .background(Color(0xFF212121).copy(alpha = 0.85f))
                        .padding(horizontal = 12.dp, vertical = 6.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "RUNNING: ${launchState.versionId}",
                        color = Color(0xFF81C784),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold
                    )
                    OutlinedButton(
                        onClick = { showControlsOverlay = !showControlsOverlay },
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text(if (showControlsOverlay) "Hide Touch" else "Show Touch", fontSize = 10.sp)
                    }
                    if (showControlsOverlay) {
                        Button(
                            onClick = {
                                if (isEditMode) {
                                    touchManager.saveActiveProfile()
                                    viewModel.saveCustomButtonLayout()
                                    Toast.makeText(context, "Layout Saved!", Toast.LENGTH_SHORT).show()
                                }
                                isEditMode = !isEditMode
                            },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isEditMode) Color(0xFF2E7D32) else Color(0xFF1976D2)
                            ),
                            modifier = Modifier.height(32.dp).testTag("ingame_edit_controls_button")
                        ) {
                            Text(if (isEditMode) "SAVE POS" else "EDIT POS", fontSize = 10.sp)
                        }
                    }
                    Button(
                        onClick = { viewModel.container.launchManager.kill() },
                        colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error),
                        modifier = Modifier.height(32.dp)
                    ) {
                        Text("FORCE STOP", fontSize = 10.sp)
                    }
                }

                // In-Game Independent Virtual Touch Controls
                if (showControlsOverlay) {
                    currentLayout.controls.forEach { control ->
                        if (control.visible || isEditMode) {
                            val btnWidth = (control.effectiveWidthDp).dp
                            val btnHeight = (control.effectiveHeightDp).dp
                            val xPos = (screenW * control.xPercent).dp - (btnWidth / 2)
                            val yPos = (screenH * control.yPercent).dp - (btnHeight / 2)
                            val isPressed = pressedControlIds.contains(control.id)

                            val shapeModifier = when (control.shape) {
                                ButtonShape.CIRCLE -> CircleShape
                                ButtonShape.ROUNDED -> RoundedCornerShape(control.cornerRadiusDp.dp)
                                ButtonShape.SQUARE -> RoundedCornerShape(3.dp)
                                ButtonShape.MINECRAFT_STYLE -> RoundedCornerShape(4.dp)
                                ButtonShape.TRANSPARENT -> RoundedCornerShape(6.dp)
                                ButtonShape.MINIMAL -> RoundedCornerShape(8.dp)
                            }

                            val bgAlpha = if (isPressed) (control.opacity + 0.2f).coerceAtMost(1.0f) else control.opacity
                            val backgroundColor = if (isEditMode) {
                                Color(0xFF1976D2).copy(alpha = 0.85f)
                            } else if (isPressed) {
                                Color(0xFF81C784).copy(alpha = bgAlpha)
                            } else {
                                when (control.shape) {
                                    ButtonShape.MINECRAFT_STYLE -> Color(0xFF37474F).copy(alpha = bgAlpha)
                                    ButtonShape.CIRCLE -> Color(0xFF263238).copy(alpha = bgAlpha)
                                    ButtonShape.SQUARE -> Color(0xFF263238).copy(alpha = bgAlpha)
                                    ButtonShape.ROUNDED -> Color(0xFF263238).copy(alpha = bgAlpha)
                                    ButtonShape.TRANSPARENT -> Color.White.copy(alpha = 0.05f * bgAlpha)
                                    ButtonShape.MINIMAL -> Color.Black.copy(alpha = 0.35f * bgAlpha)
                                }
                            }

                            val borderColor = if (isEditMode) {
                                Color(0xFFFFEB3B)
                            } else if (control.hasBorder) {
                                if (isPressed) Color(0xFFA5D6A7) else Color.White.copy(alpha = 0.4f)
                            } else {
                                Color.Transparent
                            }

                            if (control.type == ControlType.JOYSTICK) {
                                // Dynamic Joystick
                                var joyPosX by remember { mutableFloatStateOf(0f) }
                                var joyPosY by remember { mutableFloatStateOf(0f) }
                                val joyMaxRadius = control.joystickMaxRadiusDp

                                Box(
                                    modifier = Modifier
                                        .offset(x = xPos, y = yPos)
                                        .size(btnWidth, btnHeight)
                                        .clip(CircleShape)
                                        .background(backgroundColor)
                                        .border(2.dp, borderColor, CircleShape)
                                        .pointerInput(control.id, isEditMode, screenW, screenH) {
                                            if (isEditMode) {
                                                detectDragGestures { change, dragAmount ->
                                                    change.consume()
                                                    val deltaXPercent = dragAmount.x / (screenW * density)
                                                    val deltaYPercent = dragAmount.y / (screenH * density)
                                                    val newX = (control.xPercent + deltaXPercent).coerceIn(0.02f, 0.98f)
                                                    val newY = (control.yPercent + deltaYPercent).coerceIn(0.02f, 0.98f)
                                                    touchManager.updateControl(control.copy(xPercent = newX, yPercent = newY))
                                                }
                                            } else {
                                                val halfW = size.width / 2f
                                                val halfH = size.height / 2f
                                                detectDragGestures(
                                                    onDragStart = { offset ->
                                                        val dx = (offset.x - halfW).coerceIn(-joyMaxRadius, joyMaxRadius)
                                                        val dy = (offset.y - halfH).coerceIn(-joyMaxRadius, joyMaxRadius)
                                                        joyPosX = dx
                                                        joyPosY = dy
                                                        touchManager.onJoystickMove(dx, dy, joyMaxRadius, control.joystickDeadZone)
                                                    },
                                                    onDrag = { change, dragAmount ->
                                                        change.consume()
                                                        val dx = (joyPosX + dragAmount.x).coerceIn(-joyMaxRadius, joyMaxRadius)
                                                        val dy = (joyPosY + dragAmount.y).coerceIn(-joyMaxRadius, joyMaxRadius)
                                                        joyPosX = dx
                                                        joyPosY = dy
                                                        touchManager.onJoystickMove(dx, dy, joyMaxRadius, control.joystickDeadZone)
                                                    },
                                                    onDragEnd = {
                                                        joyPosX = 0f
                                                        joyPosY = 0f
                                                        touchManager.onJoystickRelease()
                                                    },
                                                    onDragCancel = {
                                                        joyPosX = 0f
                                                        joyPosY = 0f
                                                        touchManager.onJoystickRelease()
                                                    }
                                                )
                                            }
                                        }
                                        .testTag("virtual_btn_${control.id}"),
                                    contentAlignment = Alignment.Center
                                ) {
                                    // Joystick knob
                                    Box(
                                        modifier = Modifier
                                            .offset { IntOffset(joyPosX.roundToInt(), joyPosY.roundToInt()) }
                                            .size(btnWidth * 0.42f)
                                            .clip(CircleShape)
                                            .background(Color.White.copy(alpha = 0.45f * control.opacity))
                                            .border(1.5.dp, Color.White.copy(alpha = 0.6f), CircleShape)
                                    )
                                }
                            } else if (control.type == ControlType.TOUCH_AREA) {
                                // Camera Look Touchpad
                                Box(
                                    modifier = Modifier
                                        .offset(x = xPos, y = yPos)
                                        .size(btnWidth, btnHeight)
                                        .clip(shapeModifier)
                                        .background(backgroundColor)
                                        .border(if (isEditMode) 2.dp else 1.dp, borderColor, shapeModifier)
                                        .pointerInput(control.id, isEditMode, screenW, screenH) {
                                            if (isEditMode) {
                                                detectDragGestures { change, dragAmount ->
                                                    change.consume()
                                                    val deltaXPercent = dragAmount.x / (screenW * density)
                                                    val deltaYPercent = dragAmount.y / (screenH * density)
                                                    val newX = (control.xPercent + deltaXPercent).coerceIn(0.02f, 0.98f)
                                                    val newY = (control.yPercent + deltaYPercent).coerceIn(0.02f, 0.98f)
                                                    touchManager.updateControl(control.copy(xPercent = newX, yPercent = newY))
                                                }
                                            } else {
                                                detectDragGestures { change, dragAmount ->
                                                    change.consume()
                                                    touchManager.onCameraLook(
                                                        dragAmount.x,
                                                        dragAmount.y,
                                                        control.cameraSensitivity,
                                                        control.cameraInvertY,
                                                        control.cameraHorizontalSens,
                                                        control.cameraVerticalSens
                                                    )
                                                }
                                            }
                                        }
                                        .testTag("virtual_btn_${control.id}"),
                                    contentAlignment = Alignment.Center
                                ) {
                                    if (isEditMode) {
                                        Text(
                                            text = control.displayLabel,
                                            color = Color.White,
                                            fontWeight = FontWeight.Bold,
                                            fontSize = 11.sp
                                        )
                                    }
                                }
                            } else {
                                // Independent Button / Hotbar / Key
                                Box(
                                    modifier = Modifier
                                        .offset(x = xPos, y = yPos)
                                        .size(btnWidth, btnHeight)
                                        .clip(shapeModifier)
                                        .background(backgroundColor)
                                        .border(if (isEditMode) 2.dp else 1.5.dp, borderColor, shapeModifier)
                                        .pointerInput(control.id, isEditMode, screenW, screenH) {
                                            if (isEditMode) {
                                                detectDragGestures { change, dragAmount ->
                                                    change.consume()
                                                    val deltaXPercent = dragAmount.x / (screenW * density)
                                                    val deltaYPercent = dragAmount.y / (screenH * density)
                                                    val newX = (control.xPercent + deltaXPercent).coerceIn(0.02f, 0.98f)
                                                    val newY = (control.yPercent + deltaYPercent).coerceIn(0.02f, 0.98f)
                                                    touchManager.updateControl(control.copy(xPercent = newX, yPercent = newY))
                                                }
                                            } else {
                                                detectTapGestures(
                                                    onPress = { _ ->
                                                        // High-level Compose gestures do not expose MotionEvent pointer IDs.
                                                        // Allocate a monotonic owner token so simultaneous buttons remain independent.
                                                        val pointerId = touchManager.allocatePointerToken()
                                                        touchManager.onControlPointerDown(control, pointerId)
                                                        try {
                                                            tryAwaitRelease()
                                                        } finally {
                                                            touchManager.onControlPointerUp(pointerId)
                                                        }
                                                    }
                                                )
                                            }
                                        }
                                        .testTag("virtual_btn_${control.id}"),
                                    contentAlignment = Alignment.Center
                                ) {
                                    // 3D Bevel for Minecraft style
                                    if (control.shape == ButtonShape.MINECRAFT_STYLE) {
                                        Box(
                                            modifier = Modifier
                                                .fillMaxSize()
                                                .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(4.dp))
                                        )
                                    }

                                    Text(
                                        text = control.displayLabel,
                                        color = Color.White,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = (12 * control.sizeScale).sp,
                                        textAlign = TextAlign.Center
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        is LaunchState.Exited -> {
            // Exit Screen: shows session length, exit code, and crash analyzer if non-zero
            Box(
                modifier = modifier
                    .fillMaxSize()
                    .background(Color(0xFF0D1117).copy(alpha = 0.95f)),
                contentAlignment = Alignment.Center
            ) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth(0.9f)
                        .padding(16.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            if (launchState.exitCode == 0) {
                                Icon(imageVector = Icons.Default.Check, contentDescription = null, tint = Color(0xFF2E7D32), modifier = Modifier.size(28.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "Minecraft Closed Normally",
                                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                                )
                            } else {
                                Icon(imageVector = Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(28.dp))
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "Minecraft Exited with Code ${launchState.exitCode}",
                                    style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                                    color = MaterialTheme.colorScheme.error
                                )
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Session Duration: ${launchState.sessionDurationMs / 1000} seconds",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        // Crash Diagnosis Card
                        if (launchState.crashAnalysis != null) {
                            val crash = launchState.crashAnalysis
                            Spacer(modifier = Modifier.height(16.dp))
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                            ) {
                                Column(modifier = Modifier.padding(12.dp)) {
                                    Text(
                                        text = "CRASH DIAGNOSTIC: ${crash.summary}",
                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                        color = MaterialTheme.colorScheme.error
                                    )
                                    Spacer(modifier = Modifier.height(4.dp))
                                    crash.possibleCauses.forEach { cause ->
                                        Text(text = "• $cause", style = MaterialTheme.typography.bodySmall)
                                    }

                                    Spacer(modifier = Modifier.height(8.dp))
                                    Text(
                                        text = "Recommended Fix:",
                                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                        color = Color(0xFF81C784)
                                    )
                                    crash.recommendations.forEach { rec ->
                                        Text(text = "• $rec", style = MaterialTheme.typography.bodySmall)
                                    }
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(20.dp))
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Button(
                                onClick = { viewModel.resetLaunchToHome() },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Return to Launcher")
                            }

                            OutlinedButton(
                                onClick = {
                                    val text = LauncherLogger.getLogsAsText()
                                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                                    clipboard.setPrimaryClip(ClipData.newPlainText("Minecraft Crash Log", text))
                                    Toast.makeText(context, "Log copied to clipboard", Toast.LENGTH_SHORT).show()
                                },
                                modifier = Modifier.weight(1f)
                            ) {
                                Text("Copy Log")
                            }
                        }
                    }
                }
            }
        }

        is LaunchState.Error -> {
            Box(
                modifier = modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.85f)),
                contentAlignment = Alignment.Center
            ) {
                Card(
                    modifier = Modifier.fillMaxWidth(0.9f),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Warning, contentDescription = null, tint = MaterialTheme.colorScheme.error)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(text = "Launch Failed", style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold))
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(text = launchState.message, style = MaterialTheme.typography.bodyMedium)
                        Spacer(modifier = Modifier.height(16.dp))
                        Button(onClick = { viewModel.resetLaunchToHome() }) {
                            Text("Dismiss")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StepIndicator(stepNumber: Int, title: String, currentStep: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = "Step $stepNumber: $title",
            style = MaterialTheme.typography.bodyMedium,
            color = if (stepNumber <= currentStep) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.5f)
        )

        if (stepNumber < currentStep) {
            Icon(imageVector = Icons.Default.Check, contentDescription = "Done", tint = Color(0xFF2E7D32), modifier = Modifier.size(18.dp))
        } else if (stepNumber == currentStep) {
            CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
        }
    }
}
