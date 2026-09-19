package com.example.ui.screens

import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsHoveredAsState
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Leaderboard
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Store
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.skin.SkinManagerDialog
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import com.example.ui.components.StatTile
import com.example.ui.components.StatusBadge
import com.example.ui.theme.DiamondCyan
import com.example.ui.theme.GrassGreen
import com.example.ui.theme.SuccessGreen

/**
 * Premium launcher home. The visual parameters are intentionally kept here so the
 * screen can be reskinned without changing navigation or launcher logic.
 */
@Composable
fun HomeScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier,
    title: String = "CraftDroid",
    subtitle: String = "Play Minecraft Java anywhere",
    primaryAccent: Color = DiamondCyan,
    secondaryAccent: Color = GrassGreen,
    backgroundBrush: Brush = Brush.verticalGradient(
        listOf(Color(0xFF02070D), Color(0xFF06141B), Color(0xFF02070D))
    )
) {
    val uiState by viewModel.homeUiState.collectAsState()
    val showAuthRequiredDialog by viewModel.showAuthRequiredDialog.collectAsState()
    val scrollState = rememberScrollState()
    var showSkinManager by remember { mutableStateOf(false) }
    var utilityDialog by remember { mutableStateOf<String?>(null) }

    val playInteraction = remember { MutableInteractionSource() }
    val playPressed by playInteraction.collectIsPressedAsState()
    val playHovered by playInteraction.collectIsHoveredAsState()
    val pulse = rememberInfiniteTransition(label = "playPulse").animateFloat(
        initialValue = 1f,
        targetValue = 1.018f,
        animationSpec = infiniteRepeatable(tween(1200), RepeatMode.Reverse),
        label = "playScale"
    )
    val playScale = if (playPressed) 0.97f else if (playHovered) 1.035f else pulse.value

    val accent = MaterialTheme.colorScheme.primary
    val muted = MaterialTheme.colorScheme.onSurfaceVariant

    Box(
        modifier = modifier.fillMaxSize().background(backgroundBrush)
    ) {
        // Lightweight animated ambient background: gives depth without requiring image assets.
        Box(
            Modifier
                .size(300.dp)
                .offset(x = 360.dp, y = (-70).dp)
                .clip(CircleShape)
                .background(primaryAccent.copy(alpha = 0.075f))
        )
        Box(
            Modifier
                .size(240.dp)
                .offset(x = (-90).dp, y = 330.dp)
                .clip(CircleShape)
                .background(secondaryAccent.copy(alpha = 0.06f))
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(horizontal = 18.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Brand / notification / profile header.
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        Modifier.size(48.dp).clip(RoundedCornerShape(15.dp)).background(
                            Brush.linearGradient(listOf(secondaryAccent, primaryAccent))
                        ),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("C", color = Color.White, fontWeight = FontWeight.Black, fontSize = 27.sp)
                    }
                    Spacer(Modifier.width(12.dp))
                    Column {
                        Text(title.uppercase(), style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Black, letterSpacing = 1.1.sp))
                        Text(subtitle, style = MaterialTheme.typography.labelSmall, color = muted)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(contentAlignment = Alignment.TopEnd) {
                        IconButton(onClick = { utilityDialog = "Notifications" }, modifier = Modifier.testTag("notifications_button")) {
                            Icon(Icons.Default.Info, "Notifications")
                        }
                        NotificationBadge(2)
                    }
                    if (uiState.selectedAccount != null) {
                        IconButton(onClick = { showSkinManager = true }, modifier = Modifier.testTag("home_skin_button")) {
                            Icon(Icons.Default.Palette, "Customize skin")
                        }
                    }
                    IconButton(onClick = { viewModel.navigateTo(LauncherScreen.SETTINGS) }, modifier = Modifier.testTag("settings_button")) {
                        Icon(Icons.Default.Settings, "Settings")
                    }
                }
            }

            // Resource strip: launcher-local resources are presentation-only and ready for a future store service.
            Surface(shape = RoundedCornerShape(18.dp), color = Color.White.copy(alpha = .045f), tonalElevation = 0.dp) {
                Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                    ResourcePill("●", "1,250", "Coins", Color(0xFFFFD54F))
                    Spacer(Modifier.width(8.dp))
                    ResourcePill("◆", "320", "Gems", primaryAccent)
                    Spacer(Modifier.weight(1f))
                    ResourcePill("⚡", "100", "Energy", Color(0xFFB9FF73))
                }
            }

            // Account/profile card.
            Surface(
                modifier = Modifier.fillMaxWidth().clickable { viewModel.navigateTo(LauncherScreen.ACCOUNTS) },
                shape = RoundedCornerShape(22.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = .58f),
                tonalElevation = 3.dp,
                shadowElevation = 3.dp
            ) {
                Row(Modifier.padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                    if (uiState.selectedAccount?.skinUrl != null) {
                        AsyncImage(uiState.selectedAccount?.skinUrl, "Minecraft avatar", Modifier.size(46.dp).clip(CircleShape))
                    } else {
                        Box(Modifier.size(46.dp).clip(CircleShape).background(accent.copy(alpha = .14f)), contentAlignment = Alignment.Center) {
                            Icon(Icons.Default.Person, "Account", tint = accent)
                        }
                    }
                    Spacer(Modifier.width(11.dp))
                    Column(Modifier.weight(1f)) {
                        Text(uiState.selectedAccount?.username ?: "Guest profile", fontWeight = FontWeight.Bold)
                        Text(
                            uiState.selectedAccount?.let { if (it.isAuthenticated) "Microsoft account • Ready to play" else "Local profile • Limited authentication" }
                                ?: "Add a Minecraft account to get started",
                            style = MaterialTheme.typography.bodySmall,
                            color = if (uiState.selectedAccount?.isAuthenticated == true) SuccessGreen else muted
                        )
                    }
                    Text("PROFILE", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black), color = accent)
                }
            }

            // Main hero / Play area.
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(30.dp),
                colors = CardDefaults.cardColors(containerColor = Color.Transparent),
                elevation = CardDefaults.cardElevation(defaultElevation = 10.dp)
            ) {
                Box(
                    Modifier.fillMaxWidth().background(
                        Brush.linearGradient(listOf(Color(0xFF103D2C), Color(0xFF09252C), Color(0xFF07131C)))
                    ).padding(21.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(15.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
                            Column(Modifier.weight(1f)) {
                                Text("Discover. Build. Survive.", style = MaterialTheme.typography.headlineLarge.copy(fontWeight = FontWeight.Black))
                                Text("Minecraft Java Edition on Android", style = MaterialTheme.typography.bodyMedium, color = muted)
                            }
                            StatusBadge(if (uiState.isInstalled) "READY" else "SETUP", uiState.isInstalled)
                        }

                        Surface(shape = RoundedCornerShape(18.dp), color = Color.Black.copy(alpha = .2f)) {
                            Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text("SELECTED WORLD PROFILE", style = MaterialTheme.typography.labelSmall, color = muted)
                                    Text(uiState.selectedVersionId, style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Black))
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text("JAVA ${uiState.javaVersionRequirement}", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black), color = primaryAccent)
                                    Text("${uiState.ramMb} MB RAM", style = MaterialTheme.typography.bodySmall, color = muted)
                                }
                            }
                        }

                        if (uiState.isDownloading) {
                            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                                LinearProgressIndicator(progress = { uiState.downloadProgress.progressFraction }, Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(8.dp)))
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text(uiState.downloadProgress.currentFileName.ifBlank { "Preparing files…" }, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                                    Text("${(uiState.downloadProgress.progressFraction * 100).toInt()}%", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black))
                                }
                            }
                        } else {
                            Box(Modifier.fillMaxWidth().testTag("play_button_container"), contentAlignment = Alignment.Center) {
                                Button(
                                    onClick = { if (uiState.isInstalled) viewModel.launchMinecraft() else viewModel.installSelectedVersion() },
                                    interactionSource = playInteraction,
                                    modifier = Modifier.fillMaxWidth().height(64.dp).then(Modifier.graphicsScale(playScale)).testTag("main_play_button"),
                                    shape = RoundedCornerShape(20.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = primaryAccent, contentColor = Color(0xFF001516))
                                ) {
                                    Icon(if (uiState.isInstalled) Icons.Default.PlayArrow else Icons.Default.Build, null, Modifier.size(27.dp))
                                    Spacer(Modifier.width(9.dp))
                                    Text(if (uiState.isInstalled) "PLAY NOW" else "DOWNLOAD & INSTALL", fontWeight = FontWeight.Black, letterSpacing = 1.1.sp)
                                }
                            }
                        }
                    }
                }
            }

            // Secondary game-style action row.
            Text("QUICK ACCESS", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black, letterSpacing = 1.5.sp), color = accent)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                QuickAction("Settings", Icons.Default.Settings) { viewModel.navigateTo(LauncherScreen.SETTINGS) }
                QuickAction("Store", Icons.Default.Store) { utilityDialog = "Store" }
                QuickAction("Events", Icons.Default.Event) { utilityDialog = "Events" }
                QuickAction("Ranks", Icons.Default.Leaderboard) { utilityDialog = "Leaderboard" }
                QuickAction("Profile", Icons.Default.Person) { viewModel.navigateTo(LauncherScreen.ACCOUNTS) }
            }

            // Performance / launcher status.
            Text("PERFORMANCE", style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Black, letterSpacing = 1.5.sp), color = accent)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatTile("Java", "${uiState.javaVersionRequirement}", Icons.Default.Build, Modifier.weight(1f), "Runtime")
                StatTile("RAM", "${uiState.ramMb} MB", Icons.Default.Info, Modifier.weight(1f), uiState.availableStorage + " free")
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                StatTile("Renderer", uiState.rendererBackend.title, Icons.Default.Settings, Modifier.weight(1f), "Graphics")
                StatTile("Version", uiState.selectedVersionId, Icons.Default.CheckCircle, Modifier.weight(1f), if (uiState.isInstalled) "Installed" else "Setup needed")
            }

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(22.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = .58f))
            ) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text("LAUNCHER HEALTH", style = MaterialTheme.typography.labelMedium, color = accent)
                            Text("Local configuration status", style = MaterialTheme.typography.titleMedium)
                        }
                        StatusBadge(if (uiState.isInstalled) "READY" else "ACTION", uiState.isInstalled)
                    }
                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = .55f))
                    StatusLine("Minecraft files", uiState.isInstalled)
                    StatusLine("Java ${uiState.javaVersionRequirement} requirement", true)
                    StatusLine("Renderer: ${uiState.rendererBackend.title}", true)
                    StatusLine("Account authenticated", uiState.selectedAccount?.isAuthenticated == true)
                }
            }

            Surface(
                modifier = Modifier.fillMaxWidth().clickable { viewModel.navigateTo(LauncherScreen.CUSTOMIZE_CONTROLS) }.testTag("home_customize_controls_card"),
                shape = RoundedCornerShape(20.dp),
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = .62f)
            ) {
                Row(Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(44.dp).clip(RoundedCornerShape(13.dp)).background(accent.copy(alpha = .12f)), contentAlignment = Alignment.Center) {
                        Icon(Icons.Default.PlayArrow, "Touch controls", tint = accent)
                    }
                    Spacer(Modifier.width(12.dp))
                    Column(Modifier.weight(1f)) {
                        Text("Touch Controls", fontWeight = FontWeight.Bold)
                        Text("Move, resize, duplicate and customize every button", style = MaterialTheme.typography.bodySmall, color = muted)
                    }
                    Text("EDIT", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black), color = accent)
                }
            }

            if (showAuthRequiredDialog) {
                AlertDialog(
                    onDismissRequest = { viewModel.dismissAuthRequiredDialog() },
                    icon = { Icon(Icons.Default.Warning, null, tint = MaterialTheme.colorScheme.error) },
                    title = { Text("Microsoft account required", fontWeight = FontWeight.Bold) },
                    text = { Text("Sign in with a legitimate Minecraft account before launching the Java client.") },
                    confirmButton = { Button(onClick = { viewModel.dismissAuthRequiredDialog(); viewModel.navigateTo(LauncherScreen.ACCOUNTS); viewModel.startMicrosoftLogin() }) { Text("Sign in") } },
                    dismissButton = { OutlinedButton(onClick = { viewModel.dismissAuthRequiredDialog() }) { Text("Back") } }
                )
            }

            utilityDialog?.let { name ->
                AlertDialog(
                    onDismissRequest = { utilityDialog = null },
                    title = { Text(name, fontWeight = FontWeight.Black) },
                    text = { Text(if (name == "Notifications") "You have 2 launcher notifications. Store, events and leaderboard services are ready for future online integration." else "$name is part of the premium CraftDroid shell. Online content integration can be connected without changing the launcher navigation.") },
                    confirmButton = { Button(onClick = { utilityDialog = null }) { Text("OK") } }
                )
            }
        }
    }

    if (showSkinManager && uiState.selectedAccount != null) {
        SkinManagerDialog(account = uiState.selectedAccount!!, viewModel = viewModel, onDismiss = { showSkinManager = false })
    }
}

@Composable
private fun ResourcePill(icon: String, value: String, label: String, color: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text(icon, color = color, fontWeight = FontWeight.Black, fontSize = 15.sp)
        Spacer(Modifier.width(5.dp))
        Column {
            Text(value, fontWeight = FontWeight.Black, fontSize = 12.sp)
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun NotificationBadge(count: Int) {
    Box(
        Modifier.size(if (count > 9) 20.dp else 17.dp).clip(CircleShape).background(MaterialTheme.colorScheme.error),
        contentAlignment = Alignment.Center
    ) {
        Text(if (count > 9) "9+" else count.toString(), color = Color.White, fontSize = 8.sp, fontWeight = FontWeight.Black)
    }
}

@Composable
private fun RowScope.QuickAction(label: String, icon: androidx.compose.ui.graphics.vector.ImageVector, onClick: () -> Unit) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val hovered by interaction.collectIsHoveredAsState()
    val scale = when { pressed -> 0.94f; hovered -> 1.04f; else -> 1f }
    Surface(
        modifier = Modifier.graphicsScale(scale).clickable(interactionSource = interaction, indication = null, onClick = onClick),
        shape = RoundedCornerShape(17.dp),
        color = Color.White.copy(alpha = .045f),
        tonalElevation = 1.dp
    ) {
        Column(Modifier.padding(vertical = 12.dp, horizontal = 4.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(icon, label, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(21.dp))
            Spacer(Modifier.height(5.dp))
            Text(label, style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold), maxLines = 1)
        }
    }
}

private fun Modifier.graphicsScale(scale: Float): Modifier = this.then(Modifier.scale(scale))

@Composable
private fun StatusLine(label: String, ok: Boolean) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(if (ok) SuccessGreen else MaterialTheme.colorScheme.tertiary))
        Spacer(Modifier.width(9.dp))
        Text(label, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
        Text(if (ok) "OK" else "ACTION", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Black), color = if (ok) SuccessGreen else MaterialTheme.colorScheme.tertiary)
    }
}
