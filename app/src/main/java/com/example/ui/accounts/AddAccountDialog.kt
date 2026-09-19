package com.example.ui.accounts

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.OpenInBrowser
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.VpnKey
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.auth.AuthState
import com.example.auth.ElyByAccountProvider
import com.example.ui.LauncherViewModel
import java.util.UUID

@Composable
fun AddAccountDialog(
    viewModel: LauncherViewModel,
    onDismiss: () -> Unit
) {
    val authState by viewModel.authState.collectAsState()
    val context = LocalContext.current

    var selectedMode by remember { mutableStateOf<AddAccountMode>(AddAccountMode.SELECT_PROVIDER) }
    var elyByCodeInput by remember { mutableStateOf("") }
    var testProfileUsername by remember { mutableStateOf("") }
    var testProfileAvatar by remember { mutableStateOf("Steve") }

    AlertDialog(
        onDismissRequest = {
            if (authState !is AuthState.Authenticating && authState !is AuthState.Polling) {
                viewModel.cancelLogin()
                viewModel.resetAuthState()
                onDismiss()
            }
        },
        modifier = Modifier
            .fillMaxWidth(0.95f)
            .testTag("add_account_dialog"),
        shape = RoundedCornerShape(24.dp),
        containerColor = MaterialTheme.colorScheme.surface,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = when (selectedMode) {
                            AddAccountMode.SELECT_PROVIDER -> "Add Account"
                            AddAccountMode.MICROSOFT_PROMPT -> "Microsoft Sign In"
                            AddAccountMode.ELY_BY_FORM -> "Sign in with Ely.by"
                            AddAccountMode.LOCAL_TEST_FORM -> "Add Offline / Local Account"
                        },
                        style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = when (selectedMode) {
                            AddAccountMode.SELECT_PROVIDER -> "Choose how you want to sign in"
                            AddAccountMode.MICROSOFT_PROMPT -> "Complete Microsoft verification"
                            AddAccountMode.ELY_BY_FORM -> "Official Ely.by OAuth2 authentication"
                            AddAccountMode.LOCAL_TEST_FORM -> "Local profile • no online authentication"
                        },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                IconButton(onClick = {
                    viewModel.cancelLogin()
                    viewModel.resetAuthState()
                    onDismiss()
                }) {
                    Icon(imageVector = Icons.Default.Close, contentDescription = "Close")
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Handle global auth state if an operation is active
                when (val state = authState) {
                    is AuthState.Authenticating -> {
                        AuthLoadingView(message = state.step)
                    }
                    is AuthState.Polling -> {
                        AuthLoadingView(message = state.message)
                    }
                    is AuthState.DeviceCodePrompt -> {
                        MicrosoftDeviceCodeView(
                            state = state,
                            onOpenBrowser = {
                                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(state.verificationUri))
                                context.startActivity(intent)
                            },
                            onCancel = {
                                viewModel.cancelLogin()
                                selectedMode = AddAccountMode.SELECT_PROVIDER
                            }
                        )
                    }
                    is AuthState.Error -> {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Row(
                                modifier = Modifier.padding(14.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Warning,
                                    contentDescription = "Error",
                                    tint = MaterialTheme.colorScheme.error
                                )
                                Spacer(modifier = Modifier.width(10.dp))
                                Column {
                                    Text(
                                        text = "Authentication Failed",
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onErrorContainer
                                    )
                                    Text(
                                        text = state.message,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onErrorContainer
                                    )
                                }
                            }
                        }
                    }
                    is AuthState.Success -> {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = Color(0xFF1E392A)),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(
                                    text = "✓ Account Added Successfully",
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF81C784)
                                )
                                Text(
                                    text = "Welcome, ${state.username}!",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = Color.White
                                )
                                Spacer(modifier = Modifier.height(10.dp))
                                Button(
                                    onClick = {
                                        viewModel.resetAuthState()
                                        onDismiss()
                                    },
                                    modifier = Modifier.fillMaxWidth(),
                                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32))
                                ) {
                                    Text("Done")
                                }
                            }
                        }
                    }
                    is AuthState.Idle -> {
                        // Display the selected sub-mode
                        when (selectedMode) {
                            AddAccountMode.SELECT_PROVIDER -> {
                                ProviderSelectionView(
                                    onSelectMicrosoft = {
                                        viewModel.startMicrosoftLogin()
                                        selectedMode = AddAccountMode.MICROSOFT_PROMPT
                                    },
                                    onSelectElyBy = {
                                        selectedMode = AddAccountMode.ELY_BY_FORM
                                    },
                                    onSelectLocalTest = {
                                        selectedMode = AddAccountMode.LOCAL_TEST_FORM
                                    }
                                )
                            }
                            AddAccountMode.MICROSOFT_PROMPT -> {
                                Text("Connecting to Microsoft OAuth services...")
                            }
                            AddAccountMode.ELY_BY_FORM -> {
                                ElyByLoginFormView(
                                    codeInput = elyByCodeInput,
                                    onCodeChange = { elyByCodeInput = it },
                                    onOpenBrowser = {
                                        val elyProvider = viewModel.container.elyByProvider
                                        val url = elyProvider.buildAuthorizationUrlForRuntime()
                                        val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                                        context.startActivity(intent)
                                    },
                                    onSubmit = {
                                        if (elyByCodeInput.isNotBlank()) {
                                            viewModel.loginWithElyBy(elyByCodeInput.trim())
                                        }
                                    },
                                    onBack = {
                                        selectedMode = AddAccountMode.SELECT_PROVIDER
                                    }
                                )
                            }
                            AddAccountMode.LOCAL_TEST_FORM -> {
                                LocalTestProfileFormView(
                                    username = testProfileUsername,
                                    onUsernameChange = { testProfileUsername = it },
                                    selectedAvatar = testProfileAvatar,
                                    onAvatarSelect = { testProfileAvatar = it },
                                    onCreate = {
                                        viewModel.createLocalTestProfile(
                                            username = testProfileUsername.ifBlank { "Player" },
                                            testUuid = null,
                                            avatar = testProfileAvatar
                                        )
                                    },
                                    onBack = {
                                        selectedMode = AddAccountMode.SELECT_PROVIDER
                                    }
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {}
    )
}

private enum class AddAccountMode {
    SELECT_PROVIDER,
    MICROSOFT_PROMPT,
    ELY_BY_FORM,
    LOCAL_TEST_FORM
}

@Composable
private fun ProviderSelectionView(
    onSelectMicrosoft: () -> Unit,
    onSelectElyBy: () -> Unit,
    onSelectLocalTest: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        // 1. Microsoft Card
        ProviderCard(
            providerName = "Microsoft",
            badgeText = "OFFICIAL",
            badgeColor = Color(0xFF0078D4),
            description = "Official Minecraft account",
            actionText = "Sign in with Microsoft",
            icon = Icons.Default.VpnKey,
            iconTint = Color(0xFF0078D4),
            onClick = onSelectMicrosoft,
            testTag = "provider_card_microsoft"
        )

        // 2. Ely.by Card
        ProviderCard(
            providerName = "Ely.by",
            badgeText = "ELY.BY",
            badgeColor = Color(0xFF388E3C),
            description = "Ely.by account authentication",
            actionText = "Sign in with Ely.by",
            icon = Icons.Default.Cloud,
            iconTint = Color(0xFF4CAF50),
            onClick = onSelectElyBy,
            testTag = "provider_card_elyby"
        )

        // 3. Local Test Profile Card
        ProviderCard(
            providerName = "Offline / Local",
            badgeText = "LOCAL • NO ONLINE AUTH",
            badgeColor = Color(0xFFE65100),
            description = "Pojav-style offline/local profile with a persistent username and offline UUID. No Microsoft token is created.",
            actionText = "Add Offline / Local Profile",
            icon = Icons.Default.Person,
            iconTint = Color(0xFFFF9800),
            onClick = onSelectLocalTest,
            testTag = "provider_card_local_test"
        )
    }
}

@Composable
private fun ProviderCard(
    providerName: String,
    badgeText: String,
    badgeColor: Color,
    description: String,
    actionText: String,
    icon: ImageVector,
    iconTint: Color,
    onClick: () -> Unit,
    testTag: String
) {
    Card(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .testTag(testTag),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f)),
        border = androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                modifier = Modifier
                    .size(46.dp)
                    .clip(CircleShape)
                    .background(iconTint.copy(alpha = 0.15f)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = icon,
                    contentDescription = "$providerName icon",
                    tint = iconTint,
                    modifier = Modifier.size(24.dp)
                )
            }

            Spacer(modifier = Modifier.width(14.dp))

            Column(modifier = Modifier.weight(1f)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = providerName,
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Surface(
                        color = badgeColor.copy(alpha = 0.15f),
                        shape = RoundedCornerShape(4.dp)
                    ) {
                        Text(
                            text = badgeText,
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                            color = badgeColor,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = description,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = actionText,
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.SemiBold),
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Icon(
                imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                contentDescription = "Select $providerName",
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp)
            )
        }
    }
}

@Composable
private fun ElyByLoginFormView(
    codeInput: String,
    onCodeChange: (String) -> Unit,
    onOpenBrowser: () -> Unit,
    onSubmit: () -> Unit,
    onBack: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Card(
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.Top
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(20.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Text(
                    text = "Sign in via official Ely.by OAuth2. Tap 'Open in Browser' to log in and authorize CraftDroid Launcher, then paste your authorization code below.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        Button(
            onClick = onOpenBrowser,
            modifier = Modifier
                .fillMaxWidth()
                .testTag("elyby_open_browser_button"),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF388E3C))
        ) {
            Icon(imageVector = Icons.Default.OpenInBrowser, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Open Ely.by Login in Browser")
        }

        OutlinedTextField(
            value = codeInput,
            onValueChange = onCodeChange,
            modifier = Modifier
                .fillMaxWidth()
                .testTag("elyby_code_input"),
            label = { Text("Authorization Code or Token") },
            placeholder = { Text("Paste received code or token") },
            singleLine = true
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Back")
            }
            Button(
                onClick = onSubmit,
                enabled = codeInput.isNotBlank(),
                modifier = Modifier
                    .weight(1f)
                    .testTag("elyby_submit_button")
            ) {
                Text("Sign In")
            }
        }
    }
}

@Composable
private fun LocalTestProfileFormView(
    username: String,
    onUsernameChange: (String) -> Unit,
    selectedAvatar: String,
    onAvatarSelect: (String) -> Unit,
    onCreate: () -> Unit,
    onBack: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        // Warning Banner
        Card(
            colors = CardDefaults.cardColors(containerColor = Color(0xFF3E2723)),
            shape = RoundedCornerShape(12.dp),
            border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFF9800))
        ) {
            Row(
                modifier = Modifier.padding(12.dp),
                verticalAlignment = Alignment.Top
            ) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = "Warning",
                    tint = Color(0xFFFF9800),
                    modifier = Modifier.size(22.dp)
                )
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "OFFLINE / LOCAL ACCOUNT • Pojav-style",
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFFFB74D),
                        style = MaterialTheme.typography.labelMedium
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "This creates a Pojav-style Local Account: choose a username, create the profile, select it in Account Manager, then launch an already-installed version. No Microsoft token is created, and online-mode server authentication is not available.",
                        style = MaterialTheme.typography.bodySmall,
                        color = Color(0xFFFFE082)
                    )
                }
            }
        }

        OutlinedTextField(
            value = username,
            onValueChange = onUsernameChange,
            modifier = Modifier
                .fillMaxWidth()
                .testTag("offline_account_username_input"),
            label = { Text("Username") },
            placeholder = { Text("Enter username (e.g. Steve)") },
            singleLine = true
        )

        Text(
            text = "Avatar (Optional):",
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            val avatars = listOf("Steve", "Alex", "Cyberpunk", "Netherite")
            avatars.forEach { av ->
                val isSelected = selectedAvatar == av
                Surface(
                    onClick = { onAvatarSelect(av) },
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(8.dp))
                        .border(
                            width = if (isSelected) 2.dp else 1.dp,
                            color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outlineVariant,
                            shape = RoundedCornerShape(8.dp)
                        ),
                    color = if (isSelected) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface
                ) {
                    Box(modifier = Modifier.padding(8.dp), contentAlignment = Alignment.Center) {
                        Text(
                            text = av,
                            style = MaterialTheme.typography.labelSmall,
                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(6.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Back")
            }
            Button(
                onClick = onCreate,
                modifier = Modifier
                    .weight(1f)
                    .testTag("create_offline_account_button"),
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE65100))
            ) {
                Text("ADD OFFLINE ACCOUNT")
            }
        }
    }
}

@Composable
private fun AuthLoadingView(message: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        CircularProgressIndicator(modifier = Modifier.size(42.dp))
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = message,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun MicrosoftDeviceCodeView(
    state: AuthState.DeviceCodePrompt,
    onOpenBrowser: () -> Unit,
    onCancel: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "ENTER THIS CODE IN YOUR BROWSER",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = state.userCode,
                style = MaterialTheme.typography.headlineLarge.copy(
                    fontWeight = FontWeight.Black,
                    letterSpacing = 4.sp,
                    fontFamily = FontFamily.Monospace
                ),
                color = MaterialTheme.colorScheme.primary
            )
            Spacer(modifier = Modifier.height(10.dp))
            Text(
                text = "Visit: ${state.verificationUri}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface
            )
            Spacer(modifier = Modifier.height(14.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = onOpenBrowser,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Open Browser")
                }
                OutlinedButton(
                    onClick = onCancel,
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Cancel")
                }
            }
        }
    }
}
