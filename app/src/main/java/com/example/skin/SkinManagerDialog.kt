package com.example.skin

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CloudUpload
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Face
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Layers
import androidx.compose.material.icons.filled.Palette
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.example.core.db.AccountEntity
import com.example.ui.LauncherViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SkinManagerDialog(
    account: AccountEntity,
    viewModel: LauncherViewModel,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val skinManager = viewModel.container.skinManager

    var activeTab by remember { mutableIntStateOf(0) }
    var currentModel by remember { mutableStateOf(SkinModel.fromId(account.skinModel)) }
    var activeBitmap by remember { mutableStateOf<Bitmap?>(null) }
    var isOuterLayersEnabled by remember { mutableStateOf(true) }
    var isLoading by remember { mutableStateOf(false) }
    var statusMessage by remember { mutableStateOf<String?>(null) }

    // Load initial skin bitmap
    LaunchedEffect(account.skinUrl, account.avatarType) {
        withContext(Dispatchers.IO) {
            val bmp = skinManager.loadSkinBitmap(account.skinUrl)
                ?: SkinPresets.findById(account.avatarType)?.let { SkinTextureGenerator.generatePresetBitmap(it) }
                ?: SkinTextureGenerator.generatePresetBitmap(SkinPresets.presets.first())
            withContext(Dispatchers.Main) {
                activeBitmap = bmp
            }
        }
    }

    // Photo picker launcher (Zero-permission Android Photo Picker)
    val photoPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickVisualMedia(),
        onResult = { uri: Uri? ->
            if (uri != null) {
                coroutineScope.launch {
                    isLoading = true
                    val result = skinManager.saveCustomSkin(account.uuid, uri, currentModel)
                    if (result.isSuccess) {
                        val file = result.getOrNull()
                        val bmp = file?.let { BitmapFactory.decodeFile(it.absolutePath) }
                        activeBitmap = bmp
                        statusMessage = "Custom skin applied successfully!"
                        Toast.makeText(context, "Skin applied!", Toast.LENGTH_SHORT).show()
                    } else {
                        statusMessage = "Error: ${result.exceptionOrNull()?.message}"
                        Toast.makeText(context, "Failed to apply skin", Toast.LENGTH_LONG).show()
                    }
                    isLoading = false
                }
            }
        }
    )

    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(usePlatformDefaultWidth = false)
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth(0.95f)
                .fillMaxHeight(0.92f)
                .padding(8.dp)
                .testTag("skin_manager_dialog"),
            shape = RoundedCornerShape(20.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Header Bar
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(36.dp)
                                .clip(CircleShape)
                                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Palette,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                        Spacer(modifier = Modifier.width(10.dp))
                        Column {
                            Text(
                                text = "Minecraft Skin Manager",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Text(
                                text = "Account: ${account.username} • ${if (account.isLocalTestProfile) "Local Profile" else "Microsoft Account"}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }

                    IconButton(onClick = onDismiss) {
                        Icon(imageVector = Icons.Default.Close, contentDescription = "Close")
                    }
                }

                // Tab Bar
                TabRow(
                    selectedTabIndex = activeTab,
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                ) {
                    Tab(
                        selected = activeTab == 0,
                        onClick = { activeTab = 0 },
                        text = { Text("Preview", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) },
                        icon = { Icon(imageVector = Icons.Default.Person, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                    Tab(
                        selected = activeTab == 1,
                        onClick = { activeTab = 1 },
                        text = { Text("Add Skin", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) },
                        icon = { Icon(imageVector = Icons.Default.Image, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                    Tab(
                        selected = activeTab == 2,
                        onClick = { activeTab = 2 },
                        text = { Text("Presets", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) },
                        icon = { Icon(imageVector = Icons.Default.Face, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                    Tab(
                        selected = activeTab == 3,
                        onClick = { activeTab = 3 },
                        text = { Text("Online / URL", fontWeight = FontWeight.SemiBold, fontSize = 13.sp) },
                        icon = { Icon(imageVector = Icons.Default.Language, contentDescription = null, modifier = Modifier.size(18.dp)) }
                    )
                }

                if (isLoading) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        CircularProgressIndicator(modifier = Modifier.size(32.dp))
                    }
                }

                statusMessage?.let { msg ->
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.6f))
                            .padding(horizontal = 16.dp, vertical = 6.dp)
                    ) {
                        Text(
                            text = msg,
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
                    }
                }

                // Content Area
                Box(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    when (activeTab) {
                        0 -> SkinPreviewTab(
                            bitmap = activeBitmap,
                            model = currentModel,
                            outerLayers = isOuterLayersEnabled,
                            onModelChange = { newModel ->
                                currentModel = newModel
                                coroutineScope.launch {
                                    viewModel.container.skinManager.saveCustomSkin(
                                        account.uuid,
                                        Uri.parse(account.skinUrl ?: ""),
                                        newModel
                                    )
                                }
                            },
                            onToggleOuterLayers = { isOuterLayersEnabled = !isOuterLayersEnabled },
                            onExport = {
                                coroutineScope.launch {
                                    val skinFile = viewModel.container.fileSystem.getSkinFile(account.uuid)
                                    if (skinFile.exists()) {
                                        val res = skinManager.exportSkin(skinFile, account.username)
                                        if (res.isSuccess) {
                                            Toast.makeText(context, "Skin exported to Pictures/MinecraftSkins!", Toast.LENGTH_LONG).show()
                                        } else {
                                            Toast.makeText(context, "Export failed", Toast.LENGTH_SHORT).show()
                                        }
                                    } else {
                                        Toast.makeText(context, "No custom skin file to export", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            },
                            onReset = {
                                coroutineScope.launch {
                                    isLoading = true
                                    skinManager.resetSkin(account.uuid, currentModel)
                                    val defaultPreset = SkinPresets.presets.first()
                                    activeBitmap = SkinTextureGenerator.generatePresetBitmap(defaultPreset)
                                    statusMessage = "Skin reset to default Steve"
                                    Toast.makeText(context, "Reset to default", Toast.LENGTH_SHORT).show()
                                    isLoading = false
                                }
                            },
                            isMicrosoft = !account.isLocalTestProfile,
                            onUploadMojang = {
                                coroutineScope.launch {
                                    isLoading = true
                                    val token = viewModel.container.accountManager.getValidAccessToken(account.uuid)
                                    val skinFile = viewModel.container.fileSystem.getSkinFile(account.uuid)
                                    if (token != null && skinFile.exists()) {
                                        val res = skinManager.uploadSkinToMojang(token, skinFile, currentModel)
                                        if (res.isSuccess) {
                                            Toast.makeText(context, "Skin uploaded to Minecraft.net!", Toast.LENGTH_LONG).show()
                                            statusMessage = "Uploaded to Mojang Minecraft profile!"
                                        } else {
                                            Toast.makeText(context, "Upload failed: ${res.exceptionOrNull()?.message}", Toast.LENGTH_LONG).show()
                                        }
                                    } else {
                                        Toast.makeText(context, "Cannot upload: Needs valid token and skin file", Toast.LENGTH_SHORT).show()
                                    }
                                    isLoading = false
                                }
                            }
                        )

                        1 -> AddSkinFileTab(
                            currentModel = currentModel,
                            onModelChange = { currentModel = it },
                            onPickPhoto = {
                                photoPickerLauncher.launch(
                                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                                )
                            }
                        )

                        2 -> SkinPresetsTab(
                            selectedId = account.avatarType,
                            onSelectPreset = { preset ->
                                coroutineScope.launch {
                                    isLoading = true
                                    val res = skinManager.applyPresetSkin(account.uuid, preset)
                                    if (res.isSuccess) {
                                        activeBitmap = SkinTextureGenerator.generatePresetBitmap(preset)
                                        currentModel = preset.model
                                        statusMessage = "Applied preset: ${preset.name}"
                                        Toast.makeText(context, "Applied ${preset.name}", Toast.LENGTH_SHORT).show()
                                    }
                                    isLoading = false
                                }
                            }
                        )

                        3 -> SkinUrlTab(
                            onFetchUrl = { input ->
                                coroutineScope.launch {
                                    isLoading = true
                                    val res = if (input.startsWith("http://") || input.startsWith("https://")) {
                                        skinManager.fetchSkinFromUrl(account.uuid, input, currentModel)
                                    } else {
                                        skinManager.fetchSkinByPlayerName(account.uuid, input, currentModel)
                                    }

                                    if (res.isSuccess) {
                                        val file = res.getOrNull()
                                        activeBitmap = file?.let { BitmapFactory.decodeFile(it.absolutePath) }
                                        statusMessage = "Fetched and applied skin successfully!"
                                        Toast.makeText(context, "Skin applied!", Toast.LENGTH_SHORT).show()
                                    } else {
                                        statusMessage = "Error: ${res.exceptionOrNull()?.message}"
                                        Toast.makeText(context, "Failed to fetch skin", Toast.LENGTH_LONG).show()
                                    }
                                    isLoading = false
                                }
                            }
                        )
                    }
                }

                // Bottom Done Action
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.End
                ) {
                    Button(
                        onClick = onDismiss,
                        modifier = Modifier.testTag("skin_dialog_done_button")
                    ) {
                        Text("Done")
                    }
                }
            }
        }
    }
}

@Composable
private fun SkinPreviewTab(
    bitmap: Bitmap?,
    model: SkinModel,
    outerLayers: Boolean,
    onModelChange: (SkinModel) -> Unit,
    onToggleOuterLayers: () -> Unit,
    onExport: () -> Unit,
    onReset: () -> Unit,
    isMicrosoft: Boolean,
    onUploadMojang: () -> Unit
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        // Character 2D Front Render
        Box(
            modifier = Modifier
                .padding(top = 8.dp, bottom = 16.dp)
                .testTag("skin_character_preview"),
            contentAlignment = Alignment.Center
        ) {
            MinecraftSkinCharacterView(
                skinBitmap = bitmap,
                model = model,
                scale = 6.0f,
                showOuterLayers = outerLayers,
                modifier = Modifier.size(width = 160.dp, height = 230.dp)
            )
        }

        // Model selector (Classic 4px vs Slim 3px)
        Text(
            text = "ARM MODEL VARIANT",
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.height(6.dp))
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center
        ) {
            FilterChip(
                selected = model == SkinModel.CLASSIC,
                onClick = { onModelChange(SkinModel.CLASSIC) },
                label = { Text("Classic (4px Arms / Steve)") },
                leadingIcon = if (model == SkinModel.CLASSIC) {
                    { Icon(imageVector = Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp)) }
                } else null,
                modifier = Modifier.padding(horizontal = 4.dp)
            )
            FilterChip(
                selected = model == SkinModel.SLIM,
                onClick = { onModelChange(SkinModel.SLIM) },
                label = { Text("Slim (3px Arms / Alex)") },
                leadingIcon = if (model == SkinModel.SLIM) {
                    { Icon(imageVector = Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp)) }
                } else null,
                modifier = Modifier.padding(horizontal = 4.dp)
            )
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Outer layers toggle
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .clip(RoundedCornerShape(8.dp))
                .clickable { onToggleOuterLayers() }
                .padding(horizontal = 12.dp, vertical = 6.dp)
        ) {
            Icon(
                imageVector = Icons.Default.Layers,
                contentDescription = null,
                tint = if (outerLayers) MaterialTheme.colorScheme.primary else Color.Gray,
                modifier = Modifier.size(18.dp)
            )
            Spacer(modifier = Modifier.width(6.dp))
            Text(
                text = if (outerLayers) "Outer Layers (Hat/Jacket): ON" else "Outer Layers: OFF",
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium)
            )
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Action Buttons Row
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onExport,
                modifier = Modifier.weight(1f)
            ) {
                Icon(imageVector = Icons.Default.Download, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Save to Gallery", fontSize = 12.sp)
            }

            OutlinedButton(
                onClick = onReset,
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.outlinedButtonColors(contentColor = MaterialTheme.colorScheme.error)
            ) {
                Icon(imageVector = Icons.Default.Delete, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("Reset Skin", fontSize = 12.sp)
            }
        }

        if (isMicrosoft) {
            Spacer(modifier = Modifier.height(10.dp))
            Button(
                onClick = onUploadMojang,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
            ) {
                Icon(imageVector = Icons.Default.CloudUpload, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Upload to Minecraft.net (Mojang)", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun AddSkinFileTab(
    currentModel: SkinModel,
    onModelChange: (SkinModel) -> Unit,
    onPickPhoto: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(64.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Image,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(32.dp)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "Import Skin from Device",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Select any standard Minecraft skin PNG file (64x64 or legacy 64x32) from your device photos or files.",
                    style = MaterialTheme.typography.bodySmall,
                    textAlign = TextAlign.Center,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Model format choice before picking
                Text(
                    text = "Preferred Arm Model:",
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold)
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = currentModel == SkinModel.CLASSIC,
                        onClick = { onModelChange(SkinModel.CLASSIC) },
                        label = { Text("Classic (4px)") }
                    )
                    FilterChip(
                        selected = currentModel == SkinModel.SLIM,
                        onClick = { onModelChange(SkinModel.SLIM) },
                        label = { Text("Slim (3px)") }
                    )
                }

                Spacer(modifier = Modifier.height(20.dp))

                Button(
                    onClick = onPickPhoto,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp)
                        .testTag("pick_skin_photo_button"),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(imageVector = Icons.Default.Image, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Select Skin PNG from Photos / Files", fontWeight = FontWeight.Bold)
                }
            }
        }

        // Help card
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
        ) {
            Column(modifier = Modifier.padding(14.dp)) {
                Text(
                    text = "💡 Skin Compatibility Tips",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "• Compatible with skins downloaded from NameMC, PlanetMinecraft, Skindex, or NovaSkin.\n• The launcher automatically normalizes and mirrors legacy 64x32 skins to 64x64.\n• Outer layers (hat, jacket, sleeves, pants) are fully supported.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun SkinPresetsTab(
    selectedId: String,
    onSelectPreset: (SkinPreset) -> Unit
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Text(
            text = "Choose from 10 authentic Minecraft skin presets designed for any adventure:",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
            modifier = Modifier.fillMaxSize()
        ) {
            items(SkinPresets.presets, key = { it.id }) { preset ->
                val isSelected = selectedId == preset.id
                val presetBitmap = remember(preset.id) {
                    SkinTextureGenerator.generatePresetBitmap(preset)
                }

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .clickable { onSelectPreset(preset) }
                        .border(
                            width = if (isSelected) 2.dp else 1.dp,
                            color = if (isSelected) MaterialTheme.colorScheme.primary else Color.White.copy(alpha = 0.12f),
                            shape = RoundedCornerShape(12.dp)
                        ),
                    colors = CardDefaults.cardColors(
                        containerColor = if (isSelected) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.25f)
                        else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Box(contentAlignment = Alignment.TopEnd) {
                            MinecraftSkinHeadView(
                                skinBitmap = presetBitmap,
                                sizeDp = 48
                            )
                            if (isSelected) {
                                Box(
                                    modifier = Modifier
                                        .size(16.dp)
                                        .clip(CircleShape)
                                        .background(MaterialTheme.colorScheme.primary),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Check,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.onPrimary,
                                        modifier = Modifier.size(12.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = preset.name,
                            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
                            textAlign = TextAlign.Center
                        )
                        Text(
                            text = "${preset.category} • ${preset.model.label.take(7)}",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 10.sp
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = preset.description,
                            style = MaterialTheme.typography.bodySmall,
                            fontSize = 11.sp,
                            maxLines = 2,
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(8.dp))
                        Button(
                            onClick = { onSelectPreset(preset) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(32.dp),
                            shape = RoundedCornerShape(6.dp),
                            colors = if (isSelected) ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                            else ButtonDefaults.filledTonalButtonColors()
                        ) {
                            Text(if (isSelected) "Active" else "Apply", fontSize = 11.sp)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SkinUrlTab(
    onFetchUrl: (String) -> Unit
) {
    var input by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
            shape = RoundedCornerShape(16.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Fetch from Minecraft Username or URL",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "Type any valid Minecraft player name (e.g., Notch, Technoblade, DanTDM) or paste a direct PNG image link.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Spacer(modifier = Modifier.height(14.dp))

                OutlinedTextField(
                    value = input,
                    onValueChange = { input = it },
                    label = { Text("Player Name or Skin URL") },
                    placeholder = { Text("e.g. Notch or https://...") },
                    singleLine = true,
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("skin_url_input")
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Quick chips
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    val popularPlayers = listOf("Notch", "Technoblade", "Dream", "DanTDM")
                    popularPlayers.forEach { name ->
                        FilterChip(
                            selected = input == name,
                            onClick = { input = name },
                            label = { Text(name, fontSize = 11.sp) }
                        )
                    }
                }

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = { onFetchUrl(input) },
                    enabled = input.isNotBlank(),
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp)
                        .testTag("fetch_skin_button"),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(imageVector = Icons.Default.Download, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Fetch & Apply Skin", fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}
