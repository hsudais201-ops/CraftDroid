package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.renderer.RendererBackend
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import com.example.ui.components.StatusBadge

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier
) {
    val settings by viewModel.settings.collectAsState()
    val runtimes by viewModel.runtimes.collectAsState()
    val gpuInfo = viewModel.container.rendererManager.gpuInfo
    val totalDeviceRamMb = viewModel.container.settingsRepository.getDeviceTotalRamMb()
    val safeMaxRamMb = ((totalDeviceRamMb * 0.75f).toInt()).coerceAtLeast(1024)

    val scrollState = rememberScrollState()

    var ramSliderValue by remember(settings.ramMb) { mutableIntStateOf(settings.ramMb) }
    var jvmArgsText by remember(settings.customJvmArgs) { mutableStateOf(settings.customJvmArgs) }
    var touchOpacity by remember(settings.touchOpacity) { mutableFloatStateOf(settings.touchOpacity) }
    var touchScale by remember(settings.touchScale) { mutableFloatStateOf(settings.touchScale) }
    var mouseSens by remember(settings.mouseSensitivity) { mutableFloatStateOf(settings.mouseSensitivity) }
    var invertY by remember(settings.invertY) { mutableStateOf(settings.invertY) }
    var virtualMouse by remember(settings.virtualMouseEnabled) { mutableStateOf(settings.virtualMouseEnabled) }
    var showDevWarningDialog by remember { mutableStateOf(false) }

    var rendererDropdownExpanded by remember { mutableStateOf(false) }
    var javaOverrideDropdownExpanded by remember { mutableStateOf(false) }
    var curseForgeProxy by remember(settings.curseForgeProxyUrl) { mutableStateOf(settings.curseForgeProxyUrl) }

    Column(modifier = modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Launcher Settings") },
            navigationIcon = {
                IconButton(onClick = { viewModel.navigateTo(LauncherScreen.HOME) }) {
                    Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // 1. RAM & Performance Allocation
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "RAM ALLOCATION",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(
                            text = "$ramSliderValue MB",
                            style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold)
                        )
                        Text(
                            text = "Device Total: $totalDeviceRamMb MB",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    Slider(
                        value = ramSliderValue.toFloat(),
                        onValueChange = { ramSliderValue = (it / 128).toInt() * 128 },
                        onValueChangeFinished = { viewModel.updateRam(ramSliderValue) },
                        valueRange = 512f..safeMaxRamMb.toFloat(),
                        steps = ((safeMaxRamMb - 512) / 128).coerceAtLeast(1),
                        modifier = Modifier.testTag("ram_slider")
                    )

                    if (ramSliderValue > 3072 && totalDeviceRamMb <= 4096) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(imageVector = Icons.Default.Warning, contentDescription = null, tint = Color(0xFFFFA000), modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "High RAM allocation may cause OS to kill Minecraft on low memory devices.",
                                style = MaterialTheme.typography.bodySmall,
                                color = Color(0xFFFFA000)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Custom JVM Arguments",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    OutlinedTextField(
                        value = jvmArgsText,
                        onValueChange = {
                            jvmArgsText = it
                            viewModel.updateJvmArgs(it)
                        },
                        placeholder = { Text("-XX:+UseG1GC -XX:+UnlockExperimentalVMOptions") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            // 2. Minecraft installation manager
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Minecraft Versions", fontWeight = FontWeight.Bold)
                        Text(
                            "Install vanilla releases and manage installed game versions later.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Button(onClick = { viewModel.navigateTo(LauncherScreen.VERSIONS) }) {
                        Text("Manage")
                    }
                }
            }

            // 3. Java Runtime Manager
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "JAVA RUNTIMES",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    ExposedDropdownMenuBox(
                        expanded = javaOverrideDropdownExpanded,
                        onExpandedChange = { javaOverrideDropdownExpanded = !javaOverrideDropdownExpanded }
                    ) {
                        OutlinedTextField(
                            value = settings.javaMajorOverride?.let { "Java $it" } ?: "Automatic (recommended)",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Advanced Java Override") },
                            supportingText = { Text("Auto follows the Minecraft version manifest. Java 16 uses the compatible Java 17 Android runtime.") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = javaOverrideDropdownExpanded) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                        )
                        ExposedDropdownMenu(
                            expanded = javaOverrideDropdownExpanded,
                            onDismissRequest = { javaOverrideDropdownExpanded = false }
                        ) {
                            listOf<Int?>(null, 8, 16, 17, 21, 25).forEach { major ->
                                DropdownMenuItem(
                                    text = { Text(major?.let { "Java $it" } ?: "Automatic (recommended)") },
                                    onClick = {
                                        viewModel.updateJavaMajorOverride(major)
                                        javaOverrideDropdownExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    runtimes.forEach { rt ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "OpenJDK ${rt.majorVersion}",
                                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                                )
                                Text(
                                    text = rt.versionDetails,
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }

                            Row {
                                OutlinedButton(
                                    onClick = { viewModel.testJava(rt.majorVersion) },
                                    modifier = Modifier.testTag("test_java_${rt.majorVersion}")
                                ) {
                                    Text("Test")
                                }
                                Spacer(modifier = Modifier.width(6.dp))
                                Button(
                                    onClick = { viewModel.installJava(rt.majorVersion) },
                                    modifier = Modifier.testTag("install_java_${rt.majorVersion}")
                                ) {
                                    Text(if (rt.isInstalled) "Reinstall" else "Setup")
                                }
                            }
                        }
                    }
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "CONTENT SOURCES",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = curseForgeProxy,
                        onValueChange = {
                            curseForgeProxy = it
                            viewModel.updateCurseForgeProxyUrl(it)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("CurseForge HTTPS proxy URL") },
                        supportingText = {
                            Text("Keep the CurseForge API key on your server; never put it in the APK.")
                        },
                        placeholder = { Text("https://your-domain.example/api/curseforge") }
                    )
                }
            }

            // 3. Graphics & Hardware Acceleration
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "GRAPHICS & RENDERER ENGINE",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(12.dp))

                    ExposedDropdownMenuBox(
                        expanded = rendererDropdownExpanded,
                        onExpandedChange = { rendererDropdownExpanded = !rendererDropdownExpanded }
                    ) {
                        OutlinedTextField(
                            value = settings.renderer.title,
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("Selected Renderer") },
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = rendererDropdownExpanded) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                        )
                        ExposedDropdownMenu(
                            expanded = rendererDropdownExpanded,
                            onDismissRequest = { rendererDropdownExpanded = false }
                        ) {
                            RendererBackend.entries.forEach { backend ->
                                DropdownMenuItem(
                                    text = {
                                        Column {
                                            Text(backend.title, fontWeight = FontWeight.Bold)
                                            Text(backend.description, style = MaterialTheme.typography.bodySmall)
                                        }
                                    },
                                    onClick = {
                                        viewModel.updateRenderer(backend)
                                        rendererDropdownExpanded = false
                                    }
                                )
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    // GPU Diagnostics Card
                    Card(
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface.copy(alpha = 0.7f))
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text(
                                text = "HARDWARE PROBE",
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                color = MaterialTheme.colorScheme.primary
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text("GPU: ${gpuInfo.glRenderer}", style = MaterialTheme.typography.bodySmall)
                            Text("Vendor: ${gpuInfo.glVendor}", style = MaterialTheme.typography.bodySmall)
                            Text("OpenGL ES: ${gpuInfo.glEsVersion}", style = MaterialTheme.typography.bodySmall)
                            Text("Vulkan Support: ${if (gpuInfo.hasVulkan) "Yes" else "No"}", style = MaterialTheme.typography.bodySmall)
                            Text("CPU Architecture: ${gpuInfo.cpuAbi}", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }

            // 4. Touch & Controls Settings
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "CONTROLS & ON-SCREEN TOUCH",
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                        color = MaterialTheme.colorScheme.primary
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Text("Button Opacity: ${(touchOpacity * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                    Slider(
                        value = touchOpacity,
                        onValueChange = { touchOpacity = it },
                        onValueChangeFinished = {
                            viewModel.updateControls(touchOpacity, touchScale, mouseSens, invertY, virtualMouse)
                        },
                        valueRange = 0.2f..1.0f
                    )

                    Text("Button Scale: ${(touchScale * 100).toInt()}%", style = MaterialTheme.typography.bodySmall)
                    Slider(
                        value = touchScale,
                        onValueChange = { touchScale = it },
                        onValueChangeFinished = {
                            viewModel.updateControls(touchOpacity, touchScale, mouseSens, invertY, virtualMouse)
                        },
                        valueRange = 0.7f..1.5f
                    )

                    Text("Mouse Sensitivity: ${String.format("%.1fx", mouseSens)}", style = MaterialTheme.typography.bodySmall)
                    Slider(
                        value = mouseSens,
                        onValueChange = { mouseSens = it },
                        onValueChangeFinished = {
                            viewModel.updateControls(touchOpacity, touchScale, mouseSens, invertY, virtualMouse)
                        },
                        valueRange = 0.2f..3.0f
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Invert Mouse Y-Axis", style = MaterialTheme.typography.bodyMedium)
                        Switch(
                            checked = invertY,
                            onCheckedChange = {
                                invertY = it
                                viewModel.updateControls(touchOpacity, touchScale, mouseSens, invertY, virtualMouse)
                            }
                        )
                    }

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Virtual Mouse Cursor", style = MaterialTheme.typography.bodyMedium)
                        Switch(
                            checked = virtualMouse,
                            onCheckedChange = {
                                virtualMouse = it
                                viewModel.updateControls(touchOpacity, touchScale, mouseSens, invertY, virtualMouse)
                            }
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Button(
                        onClick = { viewModel.navigateTo(LauncherScreen.CUSTOMIZE_CONTROLS) },
                        modifier = Modifier.fillMaxWidth().testTag("customize_controls_button")
                    ) {
                        Icon(imageVector = Icons.Default.Build, contentDescription = null, modifier = Modifier.size(18.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Customize On-Screen Button Layout")
                    }
                }
            }

            // 6. Developer Settings
            Text(
                text = "DEVELOPER SETTINGS",
                style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold, letterSpacing = 1.sp),
                color = MaterialTheme.colorScheme.primary
            )

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f).padding(end = 16.dp)) {
                            Text(
                                text = "Enable Offline / Local Accounts",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "Allow Pojav-style offline/local profiles. They use stable offline UUIDs and a local session only; they do not authenticate to online-mode servers or create Microsoft tokens.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Switch(
                            checked = settings.enableLocalTestProfiles,
                            onCheckedChange = { checked ->
                                if (checked) {
                                    showDevWarningDialog = true
                                } else {
                                    viewModel.updateEnableLocalTestProfiles(false)
                                }
                            }
                        )
                    }

                    if (settings.enableLocalTestProfiles) {
                        Spacer(modifier = Modifier.height(12.dp))
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(Color(0xFFE65100).copy(alpha = 0.15f))
                                .padding(horizontal = 12.dp, vertical = 8.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = null,
                                tint = Color(0xFFFFB74D),
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Offline Mode Active: Local profiles can be selected and launched without Microsoft sign-in.",
                                style = MaterialTheme.typography.labelSmall,
                                color = Color(0xFFFFB74D)
                            )
                        }
                    }
                }
            }
        }

        if (showDevWarningDialog) {
            AlertDialog(
                onDismissRequest = { showDevWarningDialog = false },
                icon = { Icon(Icons.Default.Warning, contentDescription = null, tint = Color(0xFFFFA000)) },
                title = { Text("Enable Offline / Local Accounts") },
                text = {
                    Text("Offline / Local Accounts are for development/testing only and do not provide Minecraft authentication or license bypass.")
                },
                confirmButton = {
                    Button(
                        onClick = {
                            viewModel.updateEnableLocalTestProfiles(true)
                            showDevWarningDialog = false
                        }
                    ) {
                        Text("Enable")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showDevWarningDialog = false }) {
                        Text("Cancel")
                    }
                }
            )
        }
    }
}
