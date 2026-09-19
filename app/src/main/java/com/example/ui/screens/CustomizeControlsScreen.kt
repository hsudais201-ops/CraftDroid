package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.FileUpload
import androidx.compose.material.icons.filled.GridOn
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowLeft
import androidx.compose.material.icons.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.ScreenRotation
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.Undo
import androidx.compose.material.icons.filled.Redo
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.input.ButtonShape
import com.example.input.ControlAction
import com.example.input.ControlCategory
import com.example.input.ControlProfile
import com.example.input.ControlType
import com.example.input.LayoutOrientation
import com.example.input.TouchControl
import com.example.input.TouchInputManager
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomizeControlsScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val touchManager = viewModel.container.touchInputManager

    val activeProfile by touchManager.activeProfile.collectAsState()
    val allProfiles by touchManager.allProfiles.collectAsState()
    val currentLayout by touchManager.currentLayout.collectAsState()
    val orientation by touchManager.orientation.collectAsState()
    val selectedId by touchManager.selectedControlId.collectAsState()
    val isGridEnabled by touchManager.isGridEnabled.collectAsState()
    val isSnapEnabled by touchManager.isSnapEnabled.collectAsState()
    val snapGridPercent by touchManager.snapGridPercent.collectAsState()
    val canUndo by touchManager.canUndo.collectAsState()
    val canRedo by touchManager.canRedo.collectAsState()

    val selectedControl = remember(selectedId, currentLayout) {
        currentLayout.controls.firstOrNull { it.id == selectedId }
    }

    // Dialog states
    var showAddDialog by remember { mutableStateOf(false) }
    var showResetConfirm by remember { mutableStateOf(false) }
    var showProfilesDialog by remember { mutableStateOf(false) }
    var showExportDialog by remember { mutableStateOf(false) }
    var showImportDialog by remember { mutableStateOf(false) }
    var exportedJsonText by remember { mutableStateOf("") }
    var importJsonInput by remember { mutableStateOf("") }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFF0F141C))
    ) {
        // TOP APP BAR
        TopAppBar(
            title = {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = "Customize Controls",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color(0xFF1E88E5).copy(alpha = 0.25f)
                        ) {
                            Text(
                                text = activeProfile.name,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = Color(0xFF64B5F6)
                            )
                        }
                    }
                    Text(
                        text = "Every control is independent • Drag to move • Tap to customize",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFF90CAF9)
                    )
                }
            },
            navigationIcon = {
                IconButton(
                    onClick = { viewModel.navigateTo(LauncherScreen.SETTINGS) },
                    modifier = Modifier.testTag("controls_back_button")
                ) {
                    Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
            },
            actions = {
                // Profile selection / management
                IconButton(
                    onClick = { showProfilesDialog = true },
                    modifier = Modifier.testTag("profile_selector_button")
                ) {
                    Icon(imageVector = Icons.Default.Settings, contentDescription = "Profiles", tint = Color(0xFF90CAF9))
                }

                // Add Control button
                Button(
                    onClick = { showAddDialog = true },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32)),
                    modifier = Modifier.padding(end = 4.dp).testTag("add_control_button")
                ) {
                    Icon(imageVector = Icons.Default.Add, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("+ ADD CONTROL", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }

                // Reset button
                OutlinedButton(
                    onClick = { showResetConfirm = true },
                    modifier = Modifier.padding(end = 4.dp).testTag("reset_controls_button")
                ) {
                    Icon(imageVector = Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("RESET", fontSize = 12.sp)
                }

                // Save button
                Button(
                    onClick = {
                        touchManager.saveActiveProfile()
                        Toast.makeText(context, "Control layout saved successfully!", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                    modifier = Modifier.padding(end = 8.dp).testTag("save_controls_button")
                ) {
                    Icon(imageVector = Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("SAVE", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = Color(0xFF131924),
                titleContentColor = Color.White
            )
        )

        // TOOLBAR CONTROLS STRIP (Grid, Snap, Safe Area, Orientation)
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF1A2230))
                .padding(horizontal = 12.dp, vertical = 6.dp)
                .horizontalScroll(rememberScrollState()),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // Editor history
            OutlinedButton(
                onClick = { touchManager.undoEditorChange() },
                enabled = canUndo,
                modifier = Modifier.height(32.dp).testTag("undo_button")
            ) {
                Icon(Icons.Default.Undo, contentDescription = "Undo", modifier = Modifier.size(14.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Undo", fontSize = 11.sp)
            }

            OutlinedButton(
                onClick = { touchManager.redoEditorChange() },
                enabled = canRedo,
                modifier = Modifier.height(32.dp).testTag("redo_button")
            ) {
                Icon(Icons.Default.Redo, contentDescription = "Redo", modifier = Modifier.size(14.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Redo", fontSize = 11.sp)
            }

            // Grid Toggle
            FilterChip(
                selected = isGridEnabled,
                onClick = { touchManager.toggleGrid() },
                label = { Text(if (isGridEnabled) "Grid: ON" else "Grid: OFF", fontSize = 11.sp) },
                leadingIcon = { Icon(Icons.Default.GridOn, contentDescription = null, modifier = Modifier.size(14.dp)) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Color(0xFF1976D2),
                    selectedLabelColor = Color.White
                ),
                modifier = Modifier.testTag("grid_toggle_button")
            )

            // Snap Toggle
            FilterChip(
                selected = isSnapEnabled,
                onClick = { touchManager.toggleSnap() },
                label = { Text(if (isSnapEnabled) "Snap: ON" else "Snap: OFF", fontSize = 11.sp) },
                colors = FilterChipDefaults.filterChipColors(
                    selectedContainerColor = Color(0xFF388E3C),
                    selectedLabelColor = Color.White
                ),
                modifier = Modifier.testTag("snap_toggle_button")
            )

            // Snap precision
            var snapMenuExpanded by remember { mutableStateOf(false) }
            Box {
                OutlinedButton(
                    onClick = { snapMenuExpanded = true },
                    enabled = isSnapEnabled,
                    modifier = Modifier.height(32.dp)
                ) {
                    Text("Snap ${(snapGridPercent * 100).toInt()}%", fontSize = 11.sp)
                }
                DropdownMenu(
                    expanded = snapMenuExpanded,
                    onDismissRequest = { snapMenuExpanded = false }
                ) {
                    listOf(0.01f to "1%", 0.025f to "2.5%", 0.05f to "5%", 0.10f to "10%", 0.20f to "20%").forEach { (step, label) ->
                        DropdownMenuItem(
                            text = { Text(label) },
                            onClick = {
                                touchManager.setSnapGridPercent(step)
                                snapMenuExpanded = false
                            }
                        )
                    }
                }
            }

            // Safe Area Reset
            OutlinedButton(
                onClick = {
                    touchManager.resetToSafeArea()
                    Toast.makeText(context, "Controls clamped to safe area", Toast.LENGTH_SHORT).show()
                },
                modifier = Modifier.height(32.dp).testTag("safe_area_button")
            ) {
                Text("Safe Area", fontSize = 11.sp)
            }

            // Orientation Toggle
            OutlinedButton(
                onClick = {
                    val next = if (orientation == LayoutOrientation.LANDSCAPE) LayoutOrientation.PORTRAIT else LayoutOrientation.LANDSCAPE
                    touchManager.setOrientation(next)
                },
                modifier = Modifier.height(32.dp).testTag("orientation_toggle_button")
            ) {
                Icon(Icons.Default.ScreenRotation, contentDescription = null, modifier = Modifier.size(14.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text(if (orientation == LayoutOrientation.LANDSCAPE) "Landscape" else "Portrait", fontSize = 11.sp)
            }

            // Total Controls Counter
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFF263238)
            ) {
                Text(
                    text = "${currentLayout.controls.size} controls (${currentLayout.controls.count { it.visible }} visible)",
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.LightGray
                )
            }
        }

        // MAIN WORKSPACE: LIVE CANVAS + INSPECTOR PANEL
        Box(modifier = Modifier.fillMaxSize()) {
            // LIVE CANVAS
            BoxWithConstraints(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color(0xFF0A0E14))
                    .pointerInput(Unit) {
                        detectTapGestures(
                            onTap = {
                                // Tap on empty canvas deselects control
                                touchManager.selectControl(null)
                            }
                        )
                    }
            ) {
                val canvasWidth = maxWidth
                val canvasHeight = maxHeight
                val density = LocalDensity.current.density

                // 1. Optional Grid Overlay
                if (isGridEnabled) {
                    Canvas(modifier = Modifier.fillMaxSize()) {
                        val stepX = size.width * 0.05f
                        val stepY = size.height * 0.05f

                        // Vertical lines
                        var x = stepX
                        while (x < size.width) {
                            drawLine(
                                color = Color.White.copy(alpha = 0.08f),
                                start = Offset(x, 0f),
                                end = Offset(x, size.height),
                                strokeWidth = 1f
                            )
                            x += stepX
                        }

                        // Horizontal lines
                        var y = stepY
                        while (y < size.height) {
                            drawLine(
                                color = Color.White.copy(alpha = 0.08f),
                                start = Offset(0f, y),
                                end = Offset(size.width, y),
                                strokeWidth = 1f
                            )
                            y += stepY
                        }
                    }
                }

                // 2. Safe Area Border Overlay (Subtle guideline)
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 16.dp, vertical = 12.dp)
                        .border(1.dp, Color.White.copy(alpha = 0.06f), RoundedCornerShape(12.dp))
                )

                // 3. Alignment guides for the selected control. These are visual-only
                // and never change the stored layout, so free positioning remains possible.
                selectedControl?.let { selected ->
                    Canvas(modifier = Modifier.fillMaxSize()) {
                        val centerX = size.width * selected.xPercent
                        val centerY = size.height * selected.yPercent
                        drawLine(
                            color = Color(0xFF64B5F6).copy(alpha = 0.55f),
                            start = Offset(centerX, 0f),
                            end = Offset(centerX, size.height),
                            strokeWidth = 1.5f
                        )
                        drawLine(
                            color = Color(0xFF64B5F6).copy(alpha = 0.55f),
                            start = Offset(0f, centerY),
                            end = Offset(size.width, centerY),
                            strokeWidth = 1.5f
                        )
                        drawCircle(
                            color = Color(0xFFFFD54F).copy(alpha = 0.85f),
                            radius = 4f,
                            center = Offset(centerX, centerY)
                        )
                    }
                }

                // 4. Render Independent Touch Controls
                currentLayout.controls.forEach { control ->
                    val isSelected = control.id == selectedId
                    val btnWidth = (control.effectiveWidthDp).dp
                    val btnHeight = (control.effectiveHeightDp).dp

                    val xPos = (canvasWidth.value * control.xPercent).dp - (btnWidth / 2)
                    val yPos = (canvasHeight.value * control.yPercent).dp - (btnHeight / 2)

                    ControlRenderItem(
                        control = control,
                        isSelected = isSelected,
                        touchManager = touchManager,
                        width = btnWidth,
                        height = btnHeight,
                        onResize = { deltaWidthDp, deltaHeightDp ->
                            val latest = touchManager.currentLayout.value.findControl(control.id) ?: control
                            val newWidth = (latest.widthDp + deltaWidthDp).coerceIn(24, 400)
                            val newHeight = (latest.heightDp + deltaHeightDp).coerceIn(24, 400)
                            touchManager.updateControl(latest.copy(widthDp = newWidth, heightDp = newHeight))
                        },
                        modifier = Modifier
                            .offset(x = xPos, y = yPos)
                            .pointerInput(control.id, canvasWidth.value, canvasHeight.value) {
                                detectDragGestures(
                                    onDragStart = {
                                        touchManager.selectControl(control.id)
                                        touchManager.beginEditorGesture()
                                    },
                                    onDrag = { change, dragAmount ->
                                        change.consume()
                                        // Accumulate deltas locally so a long drag remains continuous
                                        // even while StateFlow emits a new control instance.
                                        val deltaXPercent = dragAmount.x / (canvasWidth.value * density)
                                        val deltaYPercent = dragAmount.y / (canvasHeight.value * density)

                                        val latest = touchManager.currentLayout.value.findControl(control.id) ?: control
                                        val newX = (latest.xPercent + deltaXPercent).coerceIn(0.02f, 0.98f)
                                        val newY = (latest.yPercent + deltaYPercent).coerceIn(0.02f, 0.98f)

                                        touchManager.updateControl(
                                            latest.copy(xPercent = newX, yPercent = newY)
                                        )
                                    },
                                    onDragEnd = { touchManager.endEditorGesture() },
                                    onDragCancel = { touchManager.cancelEditorGesture() }
                                )
                            }
                            .clickable {
                                touchManager.selectControl(control.id)
                            }
                            .testTag("editor_control_${control.id}")
                    )
                }
            }

            // INSPECTOR PANEL (Bottom Drawer when a control is selected)
            androidx.compose.animation.AnimatedVisibility(
                visible = selectedControl != null,
                enter = slideInVertically(initialOffsetY = { it }),
                exit = slideOutVertically(targetOffsetY = { it }),
                modifier = Modifier.align(Alignment.BottomCenter)
            ) {
                selectedControl?.let { ctrl ->
                    ControlInspectorSheet(
                        control = ctrl,
                        onUpdate = { updated -> touchManager.updateControl(updated) },
                        onDuplicate = { touchManager.duplicateControl(ctrl.id) },
                        onBringToFront = { touchManager.bringControlToFront(ctrl.id) },
                        onSendToBack = { touchManager.sendControlToBack(ctrl.id) },
                        onMoveUp = { touchManager.moveControlUp(ctrl.id) },
                        onMoveDown = { touchManager.moveControlDown(ctrl.id) },
                        onDelete = { touchManager.deleteControl(ctrl.id) },
                        onResetSelected = { touchManager.resetSelectedControl(ctrl.id) },
                        onClose = { touchManager.selectControl(null) }
                    )
                }
            }
        }
    }

    // DIALOGS
    if (showAddDialog) {
        AddControlDialog(
            onDismiss = { showAddDialog = false },
            onCreate = { newControl ->
                touchManager.addControl(newControl)
                showAddDialog = false
                Toast.makeText(context, "Added ${newControl.name}", Toast.LENGTH_SHORT).show()
            }
        )
    }

    if (showResetConfirm) {
        AlertDialog(
            onDismissRequest = { showResetConfirm = false },
            title = { Text("Reset Current Profile?") },
            text = { Text("Reset all controls in '${activeProfile.name}' to default layout and positions?") },
            confirmButton = {
                Button(
                    onClick = {
                        touchManager.resetCurrentProfileToDefault()
                        showResetConfirm = false
                        Toast.makeText(context, "Profile reset to default", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Reset")
                }
            },
            dismissButton = {
                TextButton(onClick = { showResetConfirm = false }) {
                    Text("Cancel")
                }
            }
        )
    }

    if (showProfilesDialog) {
        ControlProfilesModal(
            activeProfile = activeProfile,
            allProfiles = allProfiles,
            onDismiss = { showProfilesDialog = false },
            onSelectProfile = { id ->
                touchManager.switchProfile(id)
                showProfilesDialog = false
            },
            onCreateNew = { name ->
                touchManager.createNewProfile(name)
            },
            onDuplicate = { id ->
                touchManager.duplicateProfile(id)
            },
            onRename = { id, newName ->
                touchManager.renameProfile(id, newName)
            },
            onDelete = { id ->
                touchManager.deleteProfile(id)
            },
            onExport = {
                exportedJsonText = touchManager.exportActiveProfile()
                showExportDialog = true
            },
            onOpenImport = {
                importJsonInput = ""
                showImportDialog = true
            }
        )
    }

    if (showExportDialog) {
        AlertDialog(
            onDismissRequest = { showExportDialog = false },
            title = { Text("Export Control Profile") },
            text = {
                Column {
                    Text("Profile: ${activeProfile.name}", fontWeight = FontWeight.Bold)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = exportedJsonText,
                        onValueChange = {},
                        readOnly = true,
                        modifier = Modifier.fillMaxWidth().height(200.dp),
                        textStyle = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("Minecraft Controls", exportedJsonText))
                        Toast.makeText(context, "Copied profile JSON to clipboard!", Toast.LENGTH_SHORT).show()
                        showExportDialog = false
                    }
                ) {
                    Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Copy JSON")
                }
            },
            dismissButton = {
                TextButton(onClick = { showExportDialog = false }) {
                    Text("Close")
                }
            }
        )
    }

    if (showImportDialog) {
        AlertDialog(
            onDismissRequest = { showImportDialog = false },
            title = { Text("Import Control Profile") },
            text = {
                Column {
                    Text("Paste a valid control profile JSON string:", style = MaterialTheme.typography.bodySmall)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = importJsonInput,
                        onValueChange = { importJsonInput = it },
                        modifier = Modifier.fillMaxWidth().height(200.dp),
                        placeholder = { Text("Paste JSON here...") },
                        textStyle = MaterialTheme.typography.bodySmall.copy(fontFamily = FontFamily.Monospace)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (importJsonInput.isBlank()) {
                            Toast.makeText(context, "Input cannot be empty", Toast.LENGTH_SHORT).show()
                            return@Button
                        }
                        val result = touchManager.importProfile(importJsonInput)
                        if (result.isSuccess) {
                            Toast.makeText(context, "Profile imported: ${result.getOrNull()?.name}", Toast.LENGTH_SHORT).show()
                            showImportDialog = false
                            showProfilesDialog = false
                        } else {
                            Toast.makeText(context, "Import failed: ${result.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                ) {
                    Text("Import")
                }
            },
            dismissButton = {
                TextButton(onClick = { showImportDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

/**
 * Visual renderer for an independent touch control in the editor.
 */
@Composable
fun ControlRenderItem(
    control: TouchControl,
    isSelected: Boolean,
    touchManager: TouchInputManager,
    width: androidx.compose.ui.unit.Dp,
    height: androidx.compose.ui.unit.Dp,
    onResize: ((deltaWidthDp: Int, deltaHeightDp: Int) -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val density = LocalDensity.current.density

    val shapeModifier = when (control.shape) {
        ButtonShape.CIRCLE -> CircleShape
        ButtonShape.ROUNDED -> RoundedCornerShape(control.cornerRadiusDp.dp)
        ButtonShape.SQUARE -> RoundedCornerShape(3.dp)
        ButtonShape.MINECRAFT_STYLE -> RoundedCornerShape(4.dp)
        ButtonShape.TRANSPARENT -> RoundedCornerShape(6.dp)
        ButtonShape.MINIMAL -> RoundedCornerShape(8.dp)
    }

    val backgroundColor = when (control.shape) {
        ButtonShape.MINECRAFT_STYLE -> Color(0xFF3A3D40).copy(alpha = control.opacity)
        ButtonShape.CIRCLE -> Color(0xFF2C3440).copy(alpha = control.opacity)
        ButtonShape.SQUARE -> Color(0xFF2C3440).copy(alpha = control.opacity)
        ButtonShape.ROUNDED -> Color(0xFF263238).copy(alpha = control.opacity)
        ButtonShape.TRANSPARENT -> Color.White.copy(alpha = 0.05f * control.opacity)
        ButtonShape.MINIMAL -> Color.Black.copy(alpha = 0.35f * control.opacity)
    }

    val borderColor = if (isSelected) {
        Color(0xFFFFD54F) // Radiant gold for selection
    } else if (control.hasBorder) {
        when (control.shape) {
            ButtonShape.MINECRAFT_STYLE -> Color(0xFF78909C).copy(alpha = 0.6f)
            ButtonShape.TRANSPARENT -> Color.White.copy(alpha = 0.3f)
            else -> Color.White.copy(alpha = 0.25f)
        }
    } else {
        Color.Transparent
    }

    val borderWidth = if (isSelected) 3.dp else 1.5.dp

    Box(
        modifier = modifier
            .size(width, height)
            .shadow(
                elevation = if (control.hasShadow && !isSelected) 4.dp else 0.dp,
                shape = shapeModifier
            )
            .clip(shapeModifier)
            .background(backgroundColor)
            .border(borderWidth, borderColor, shapeModifier),
        contentAlignment = Alignment.Center
    ) {
        // Minecraft 3D Bevel Top-Left Highlight
        if (control.shape == ButtonShape.MINECRAFT_STYLE) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(4.dp))
            )
        }

        // Special render for Joystick
        if (control.type == ControlType.JOYSTICK) {
            Box(
                modifier = Modifier
                    .size(width * 0.45f)
                    .clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.4f))
                    .border(1.5.dp, Color.White.copy(alpha = 0.6f), CircleShape)
            )
        } else if (control.type == ControlType.TOUCH_AREA) {
            // Touch Area / Camera indicator
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = control.displayLabel,
                    color = Color.White.copy(alpha = 0.7f),
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    textAlign = TextAlign.Center
                )
                Text(
                    text = "Touch-Look Area",
                    color = Color.White.copy(alpha = 0.4f),
                    fontSize = 9.sp
                )
            }
        } else {
            // Standard Button / Hotbar Label
            Text(
                text = control.displayLabel,
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = (12 * control.sizeScale).sp,
                textAlign = TextAlign.Center,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.padding(2.dp)
            )
        }

        // Hidden indicator badge
        if (!control.visible) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(Color.Black.copy(alpha = 0.5f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.VisibilityOff,
                    contentDescription = "Hidden",
                    tint = Color(0xFFEF5350),
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        // Selected corner badge
        if (isSelected) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .size(10.dp)
                    .background(Color(0xFFFFD54F), CircleShape)
            )

            // Dedicated resize handle. It is intentionally separate from the
            // drag surface so moving and resizing cannot fight for the same gesture.
            if (onResize != null) {
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomEnd)
                        .size(24.dp)
                        .background(Color(0xFFFFD54F).copy(alpha = 0.9f), RoundedCornerShape(6.dp))
                        .pointerInput(control.id, width, height) {
                            var resizeAccumulatorX = 0f
                            var resizeAccumulatorY = 0f
                            detectDragGestures(
                                onDragStart = {
                                    touchManager.beginEditorGesture()
                                    resizeAccumulatorX = 0f
                                    resizeAccumulatorY = 0f
                                },
                                onDrag = { change, dragAmount ->
                                    change.consume()
                                    resizeAccumulatorX += dragAmount.x
                                    resizeAccumulatorY += dragAmount.y
                                    val density = density
                                    val dxDp = (resizeAccumulatorX / density).roundToInt()
                                    val dyDp = (resizeAccumulatorY / density).roundToInt()
                                    if (dxDp != 0 || dyDp != 0) {
                                        onResize(dxDp, dyDp)
                                        resizeAccumulatorX = 0f
                                        resizeAccumulatorY = 0f
                                    }
                                },
                                onDragEnd = { touchManager.endEditorGesture() },
                                onDragCancel = { touchManager.cancelEditorGesture() }
                            )
                        },
                    contentAlignment = Alignment.Center
                ) {
                    Text("↘", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 14.sp)
                }
            }
        }
    }
}

/**
 * Live Inspector sheet allowing customization of position, size, opacity, action, shape, and visibility.
 */
@Composable
fun ControlInspectorSheet(
    control: TouchControl,
    onUpdate: (TouchControl) -> Unit,
    onDuplicate: () -> Unit,
    onBringToFront: () -> Unit,
    onSendToBack: () -> Unit,
    onMoveUp: () -> Unit,
    onMoveDown: () -> Unit,
    onDelete: () -> Unit,
    onResetSelected: () -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .heightIn(max = 380.dp),
        shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF161E2E)),
        elevation = CardDefaults.cardElevation(defaultElevation = 16.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(16.dp)
                .verticalScroll(rememberScrollState())
        ) {
            // HEADER
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            text = control.name,
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                            color = Color.White
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Surface(
                            shape = RoundedCornerShape(4.dp),
                            color = Color(0xFF1E88E5).copy(alpha = 0.3f)
                        ) {
                            Text(
                                text = control.type.displayName,
                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = Color(0xFF90CAF9)
                            )
                        }
                    }
                    Text(
                        text = "Action: ${control.action.actionName} | KeyCode: ${control.keyBinding}",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color.LightGray
                    )
                }

                IconButton(onClick = onClose) {
                    Icon(Icons.Default.Close, contentDescription = "Close Inspector", tint = Color.LightGray)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // 1. POSITION & NUDGE ARROWS
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Position: X ${(control.xPercent * 100).toInt()}% • Y ${(control.yPercent * 100).toInt()}%",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFF90CAF9),
                    fontWeight = FontWeight.Bold
                )

                // Nudge arrow controls
                Row {
                    IconButton(
                        onClick = { onUpdate(control.copy(xPercent = (control.xPercent - 0.01f).coerceAtLeast(0.02f))) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowLeft, contentDescription = "Left", tint = Color.White)
                    }
                    IconButton(
                        onClick = { onUpdate(control.copy(xPercent = (control.xPercent + 0.01f).coerceAtMost(0.98f))) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowRight, contentDescription = "Right", tint = Color.White)
                    }
                    IconButton(
                        onClick = { onUpdate(control.copy(yPercent = (control.yPercent - 0.01f).coerceAtLeast(0.02f))) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowUp, contentDescription = "Up", tint = Color.White)
                    }
                    IconButton(
                        onClick = { onUpdate(control.copy(yPercent = (control.yPercent + 0.01f).coerceAtMost(0.98f))) },
                        modifier = Modifier.size(32.dp)
                    ) {
                        Icon(Icons.Default.KeyboardArrowDown, contentDescription = "Down", tint = Color.White)
                    }
                }
            }

            // Precise numeric editor: normalized position (%) and base size (dp).
            var xText by remember(control.id, control.xPercent) { mutableStateOf(((control.xPercent * 100f).coerceIn(0f, 100f)).toInt().toString()) }
            var yText by remember(control.id, control.yPercent) { mutableStateOf(((control.yPercent * 100f).coerceIn(0f, 100f)).toInt().toString()) }
            var widthText by remember(control.id, control.widthDp) { mutableStateOf(control.widthDp.toString()) }
            var heightText by remember(control.id, control.heightDp) { mutableStateOf(control.heightDp.toString()) }
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                OutlinedTextField(xText, { v -> xText = v.filter(Char::isDigit).take(3); xText.toIntOrNull()?.let { onUpdate(control.copy(xPercent = (it / 100f).coerceIn(0.01f, 0.99f))) } }, label = { Text("X %", fontSize = 10.sp) }, singleLine = true, modifier = Modifier.weight(1f), textStyle = MaterialTheme.typography.bodySmall)
                OutlinedTextField(yText, { v -> yText = v.filter(Char::isDigit).take(3); yText.toIntOrNull()?.let { onUpdate(control.copy(yPercent = (it / 100f).coerceIn(0.01f, 0.99f))) } }, label = { Text("Y %", fontSize = 10.sp) }, singleLine = true, modifier = Modifier.weight(1f), textStyle = MaterialTheme.typography.bodySmall)
                OutlinedTextField(widthText, { v -> widthText = v.filter(Char::isDigit).take(3); widthText.toIntOrNull()?.let { onUpdate(control.copy(widthDp = it.coerceIn(24, 400))) } }, label = { Text("W dp", fontSize = 10.sp) }, singleLine = true, modifier = Modifier.weight(1f), textStyle = MaterialTheme.typography.bodySmall)
                OutlinedTextField(heightText, { v -> heightText = v.filter(Char::isDigit).take(3); heightText.toIntOrNull()?.let { onUpdate(control.copy(heightDp = it.coerceIn(24, 400))) } }, label = { Text("H dp", fontSize = 10.sp) }, singleLine = true, modifier = Modifier.weight(1f), textStyle = MaterialTheme.typography.bodySmall)
            }

            // 2. SIZE SLIDER (50% to 200%)
            Text(
                text = "Size: ${(control.sizeScale * 100).toInt()}%",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White
            )
            Slider(
                value = control.sizeScale,
                onValueChange = { onUpdate(control.copy(sizeScale = it)) },
                valueRange = 0.5f..2.0f,
                modifier = Modifier.fillMaxWidth()
            )

            // 3. OPACITY SLIDER (0% to 100%)
            Text(
                text = "Opacity: ${(control.opacity * 100).toInt()}%",
                style = MaterialTheme.typography.bodySmall,
                color = Color.White
            )
            Slider(
                value = control.opacity,
                onValueChange = { onUpdate(control.copy(opacity = it)) },
                valueRange = 0.0f..1.0f,
                modifier = Modifier.fillMaxWidth()
            )

            // 4. ACTION SELECTOR & SHAPE PICKER ROW
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Action Selector
                var actionExpanded by remember { mutableStateOf(false) }
                Box(modifier = Modifier.weight(1f)) {
                    OutlinedButton(
                        onClick = { actionExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Action: ${control.action.defaultLabel}",
                            fontSize = 11.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    DropdownMenu(
                        expanded = actionExpanded,
                        onDismissRequest = { actionExpanded = false }
                    ) {
                        ControlAction.entries.forEach { act ->
                            DropdownMenuItem(
                                text = { Text("[${act.category.displayName}] ${act.actionName} (${act.defaultLabel})") },
                                onClick = {
                                    onUpdate(control.copy(action = act, name = act.actionName))
                                    actionExpanded = false
                                }
                            )
                        }
                    }
                }

                // Shape Picker
                var shapeExpanded by remember { mutableStateOf(false) }
                Box(modifier = Modifier.weight(1f)) {
                    OutlinedButton(
                        onClick = { shapeExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "Shape: ${control.shape.displayName}",
                            fontSize = 11.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }
                    DropdownMenu(
                        expanded = shapeExpanded,
                        onDismissRequest = { shapeExpanded = false }
                    ) {
                        ButtonShape.entries.forEach { sh ->
                            DropdownMenuItem(
                                text = { Text(sh.displayName) },
                                onClick = {
                                    onUpdate(control.copy(shape = sh))
                                    shapeExpanded = false
                                }
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // 5. VISIBILITY TOGGLE
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (control.visible) "Visibility: Visible in-game" else "Visibility: Hidden in-game",
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (control.visible) Color(0xFF81C784) else Color(0xFFEF5350)
                )
                Switch(
                    checked = control.visible,
                    onCheckedChange = { onUpdate(control.copy(visible = it)) }
                )
            }

            // 6. JOYSTICK SPECIFIC SETTINGS
            if (control.type == ControlType.JOYSTICK) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Dead Zone: ${(control.joystickDeadZone * 100).toInt()}%",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.LightGray
                )
                Slider(
                    value = control.joystickDeadZone,
                    onValueChange = { onUpdate(control.copy(joystickDeadZone = it)) },
                    valueRange = 0.05f..0.4f
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Dynamic Joystick", style = MaterialTheme.typography.bodySmall, color = Color.White)
                        Text(
                            "Place the thumbstick under your finger on touch-down",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color.LightGray
                        )
                    }
                    Switch(
                        checked = control.joystickDynamicOrigin,
                        onCheckedChange = { onUpdate(control.copy(joystickDynamicOrigin = it)) }
                    )
                }
            }

            // 7. CAMERA SPECIFIC SETTINGS
            if (control.type == ControlType.TOUCH_AREA) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text("Invert Y Axis", style = MaterialTheme.typography.bodySmall, color = Color.White)
                    Switch(
                        checked = control.cameraInvertY,
                        onCheckedChange = { onUpdate(control.copy(cameraInvertY = it)) }
                    )
                }
                Text(
                    text = "Sensitivity: ${String.format("%.1fx", control.cameraSensitivity)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.LightGray
                )
                Slider(
                    value = control.cameraSensitivity,
                    onValueChange = { onUpdate(control.copy(cameraSensitivity = it)) },
                    valueRange = 0.2f..3.0f
                )
            }

            Spacer(modifier = Modifier.height(12.dp))

            // 8. LAYER + ACTION BUTTONS
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                OutlinedButton(onClick = onMoveDown, modifier = Modifier.weight(1f)) { Icon(Icons.Default.KeyboardArrowDown, contentDescription = null, modifier = Modifier.size(14.dp)); Spacer(modifier = Modifier.width(2.dp)); Text("Down", fontSize = 10.sp) }
                OutlinedButton(onClick = onMoveUp, modifier = Modifier.weight(1f)) { Icon(Icons.Default.KeyboardArrowUp, contentDescription = null, modifier = Modifier.size(14.dp)); Spacer(modifier = Modifier.width(2.dp)); Text("Up", fontSize = 10.sp) }
                OutlinedButton(onClick = onBringToFront, modifier = Modifier.weight(1f)) { Text("Front", fontSize = 10.sp) }
                OutlinedButton(onClick = onSendToBack, modifier = Modifier.weight(1f)) { Text("Back", fontSize = 10.sp) }
                OutlinedButton(onClick = onDuplicate, modifier = Modifier.weight(1f)) { Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(14.dp)); Spacer(modifier = Modifier.width(2.dp)); Text("Duplicate", fontSize = 10.sp) }
                OutlinedButton(onClick = onResetSelected, modifier = Modifier.weight(1f)) { Icon(Icons.Default.Refresh, contentDescription = null, modifier = Modifier.size(14.dp)); Spacer(modifier = Modifier.width(2.dp)); Text("Reset", fontSize = 10.sp) }
                Button(onClick = onDelete, colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error), modifier = Modifier.weight(1f)) { Icon(Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(14.dp)); Spacer(modifier = Modifier.width(2.dp)); Text("Delete", fontSize = 10.sp) }
            }
        }
    }
}

/**
 * Dialog to add an independent control to the live editor.
 */
@Composable
fun AddControlDialog(
    onDismiss: () -> Unit,
    onCreate: (TouchControl) -> Unit
) {
    var selectedType by remember { mutableStateOf(ControlType.BUTTON) }
    var selectedAction by remember { mutableStateOf(ControlAction.JUMP) }
    var selectedShape by remember { mutableStateOf(ButtonShape.MINECRAFT_STYLE) }
    var customName by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("+ Add Independent Control", fontWeight = FontWeight.Bold) },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Type Selector
                Text("Control Type:", style = MaterialTheme.typography.labelMedium)
                var typeExpanded by remember { mutableStateOf(false) }
                Box {
                    OutlinedButton(
                        onClick = { typeExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(selectedType.displayName)
                    }
                    DropdownMenu(
                        expanded = typeExpanded,
                        onDismissRequest = { typeExpanded = false }
                    ) {
                        ControlType.entries.forEach { type ->
                            DropdownMenuItem(
                                text = { Text(type.displayName) },
                                onClick = {
                                    selectedType = type
                                    // Set sensible default action
                                    when (type) {
                                        ControlType.JOYSTICK -> selectedAction = ControlAction.JOYSTICK_MOVE
                                        ControlType.TOUCH_AREA -> selectedAction = ControlAction.CAMERA_LOOK
                                        ControlType.HOTBAR_SLOT -> selectedAction = ControlAction.HOTBAR_1
                                        else -> {}
                                    }
                                    typeExpanded = false
                                }
                            )
                        }
                    }
                }

                // Action Selector
                Text("Assigned Action:", style = MaterialTheme.typography.labelMedium)
                var actionExpanded by remember { mutableStateOf(false) }
                Box {
                    OutlinedButton(
                        onClick = { actionExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("${selectedAction.actionName} (${selectedAction.defaultLabel})")
                    }
                    DropdownMenu(
                        expanded = actionExpanded,
                        onDismissRequest = { actionExpanded = false }
                    ) {
                        ControlAction.entries.forEach { act ->
                            DropdownMenuItem(
                                text = { Text("[${act.category.displayName}] ${act.actionName}") },
                                onClick = {
                                    selectedAction = act
                                    actionExpanded = false
                                }
                            )
                        }
                    }
                }

                // Button Shape
                Text("Button Shape:", style = MaterialTheme.typography.labelMedium)
                var shapeExpanded by remember { mutableStateOf(false) }
                Box {
                    OutlinedButton(
                        onClick = { shapeExpanded = true },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(selectedShape.displayName)
                    }
                    DropdownMenu(
                        expanded = shapeExpanded,
                        onDismissRequest = { shapeExpanded = false }
                    ) {
                        ButtonShape.entries.forEach { sh ->
                            DropdownMenuItem(
                                text = { Text(sh.displayName) },
                                onClick = {
                                    selectedShape = sh
                                    shapeExpanded = false
                                }
                            )
                        }
                    }
                }

                // Custom Label (Optional)
                OutlinedTextField(
                    value = customName,
                    onValueChange = { customName = it },
                    label = { Text("Display Name (optional)") },
                    placeholder = { Text(selectedAction.actionName) },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val name = if (customName.isNotBlank()) customName else selectedAction.actionName
                    val width = if (selectedType == ControlType.JOYSTICK) 130 else if (selectedType == ControlType.TOUCH_AREA) 320 else 56
                    val height = if (selectedType == ControlType.JOYSTICK) 130 else if (selectedType == ControlType.TOUCH_AREA) 240 else 56

                    val newCtrl = TouchControl(
                        id = "ctrl_${System.currentTimeMillis()}",
                        name = name,
                        type = selectedType,
                        action = selectedAction,
                        xPercent = 0.50f,
                        yPercent = 0.50f,
                        widthDp = width,
                        heightDp = height,
                        shape = selectedShape
                    )
                    onCreate(newCtrl)
                }
            ) {
                Text("Create Control")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

/**
 * Control Profiles management modal with Load, Duplicate, Rename, Delete, Export, Import.
 */
@Composable
fun ControlProfilesModal(
    activeProfile: ControlProfile,
    allProfiles: List<ControlProfile>,
    onDismiss: () -> Unit,
    onSelectProfile: (String) -> Unit,
    onCreateNew: (String) -> Unit,
    onDuplicate: (String) -> Unit,
    onRename: (String, String) -> Unit,
    onDelete: (String) -> Unit,
    onExport: () -> Unit,
    onOpenImport: () -> Unit
) {
    var showNewProfileDialog by remember { mutableStateOf(false) }
    var renameTargetId by remember { mutableStateOf<String?>(null) }
    var renameText by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Control Profiles", fontWeight = FontWeight.Bold)
                IconButton(onClick = onDismiss) {
                    Icon(Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "Select, duplicate, or customize layout profiles:",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.LightGray
                )

                allProfiles.forEach { profile ->
                    val isActive = profile.id == activeProfile.id
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable { onSelectProfile(profile.id) },
                        colors = CardDefaults.cardColors(
                            containerColor = if (isActive) Color(0xFF1E88E5).copy(alpha = 0.25f) else Color(0xFF1A2230)
                        ),
                        border = if (isActive) androidx.compose.foundation.BorderStroke(1.5.dp, Color(0xFF64B5F6)) else null
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = profile.name,
                                        fontWeight = FontWeight.Bold,
                                        color = if (isActive) Color(0xFF90CAF9) else Color.White
                                    )
                                    if (isActive) {
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Surface(
                                            shape = RoundedCornerShape(4.dp),
                                            color = Color(0xFF2E7D32)
                                        ) {
                                            Text(
                                                text = "ACTIVE",
                                                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp),
                                                fontSize = 9.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = Color.White
                                            )
                                        }
                                    }
                                }
                                Text(
                                    text = "${profile.landscapeLayout.controls.size} controls • ${if (profile.isCustom) "Custom" else "Built-in"}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = Color.LightGray
                                )
                            }

                            // Profile Actions Row
                            Row(horizontalArrangement = Arrangement.spacedBy(2.dp)) {
                                IconButton(
                                    onClick = { onDuplicate(profile.id) },
                                    modifier = Modifier.size(28.dp)
                                ) {
                                    Icon(Icons.Default.ContentCopy, contentDescription = "Duplicate", modifier = Modifier.size(16.dp))
                                }

                                if (profile.isCustom) {
                                    IconButton(
                                        onClick = {
                                            renameTargetId = profile.id
                                            renameText = profile.name
                                        },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(Icons.Default.Edit, contentDescription = "Rename", modifier = Modifier.size(16.dp))
                                    }

                                    IconButton(
                                        onClick = { onDelete(profile.id) },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = Color(0xFFEF5350), modifier = Modifier.size(16.dp))
                                    }
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Action buttons: New Profile, Export, Import
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = { showNewProfileDialog = true },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.Add, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("New Profile", fontSize = 11.sp)
                    }

                    OutlinedButton(
                        onClick = onExport,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.FileUpload, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Export", fontSize = 11.sp)
                    }

                    OutlinedButton(
                        onClick = onOpenImport,
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.FileDownload, contentDescription = null, modifier = Modifier.size(14.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Import", fontSize = 11.sp)
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("Done")
            }
        }
    )

    // Rename Dialog
    if (renameTargetId != null) {
        AlertDialog(
            onDismissRequest = { renameTargetId = null },
            title = { Text("Rename Profile") },
            text = {
                OutlinedTextField(
                    value = renameText,
                    onValueChange = { renameText = it },
                    singleLine = true,
                    label = { Text("Profile Name") }
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (renameText.isNotBlank()) {
                            onRename(renameTargetId!!, renameText.trim())
                        }
                        renameTargetId = null
                    }
                ) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { renameTargetId = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // New Profile Dialog
    if (showNewProfileDialog) {
        var newName by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showNewProfileDialog = false },
            title = { Text("Create New Profile") },
            text = {
                OutlinedTextField(
                    value = newName,
                    onValueChange = { newName = it },
                    singleLine = true,
                    label = { Text("Profile Name") },
                    placeholder = { Text("e.g. My PvP Layout") }
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (newName.isNotBlank()) {
                            onCreateNew(newName.trim())
                            showNewProfileDialog = false
                            onDismiss()
                        }
                    }
                ) {
                    Text("Create")
                }
            },
            dismissButton = {
                TextButton(onClick = { showNewProfileDialog = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}
