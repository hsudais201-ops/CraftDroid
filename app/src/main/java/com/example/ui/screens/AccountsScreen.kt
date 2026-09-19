package com.example.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.core.db.AccountEntity
import com.example.skin.SkinManagerDialog
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import com.example.ui.accounts.AccountCard
import com.example.ui.accounts.AccountDetailsDialog
import com.example.ui.accounts.AddAccountDialog

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AccountsScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier
) {
    val accounts by viewModel.accounts.collectAsState()

    var showAddAccountDialog by remember { mutableStateOf(false) }
    var selectedAccountForDetails by remember { mutableStateOf<AccountEntity?>(null) }
    var showSkinManagerAccount by remember { mutableStateOf<AccountEntity?>(null) }
    var accountToRename by remember { mutableStateOf<AccountEntity?>(null) }
    var accountToRemove by remember { mutableStateOf<AccountEntity?>(null) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Minecraft Accounts",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                    )
                },
                navigationIcon = {
                    IconButton(onClick = { viewModel.navigateTo(LauncherScreen.HOME) }) {
                        Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to home")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddAccountDialog = true },
                modifier = Modifier
                    .size(64.dp)
                    .testTag("add_account_fab"),
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary
            ) {
                Icon(
                    imageVector = Icons.Default.Add,
                    contentDescription = "Add Account"
                )
            }
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 16.dp, vertical = 8.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Top Overview Card
            item {
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.7f))
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "Account Manager",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "One place for Microsoft, Ely.by, and Offline / Local profiles. Your selected account is used when launching Minecraft Java.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(14.dp))
                        Button(
                            onClick = { showAddAccountDialog = true },
                            modifier = Modifier
                                .fillMaxWidth()
                                .testTag("add_account_button"),
                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                        ) {
                            Icon(imageVector = Icons.Default.Add, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "Add Account",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                        }
                    }
                }
            }

            // Quick stats / account types
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    AccountStatCard(
                        modifier = Modifier.weight(1f),
                        value = accounts.size.toString(),
                        label = "Profiles",
                        icon = Icons.Default.Person
                    )
                    AccountStatCard(
                        modifier = Modifier.weight(1f),
                        value = if (accounts.any { it.isSelected }) "1" else "0",
                        label = "Active",
                        icon = Icons.Default.Security
                    )
                    AccountStatCard(
                        modifier = Modifier.weight(1f),
                        value = accounts.count { it.providerType == "LOCAL_TEST" }.toString(),
                        label = "Offline",
                        icon = Icons.Default.Lock
                    )
                }
            }

            // Accounts List Header
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "YOUR PROFILES",
                        style = MaterialTheme.typography.labelMedium.copy(
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp
                        ),
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }

            if (accounts.isEmpty()) {
                item {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f))
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(32.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Person,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.size(48.dp)
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = "No Accounts Added",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "Tap the + button to add Microsoft, Ely.by, or an Offline / Local profile.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                textAlign = androidx.compose.ui.text.style.TextAlign.Center
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Button(onClick = { showAddAccountDialog = true }) {
                                Icon(imageVector = Icons.Default.Add, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Add Account")
                            }
                        }
                    }
                }
            } else {
                items(accounts, key = { it.uuid }) { account ->
                    AccountCard(
                        account = account,
                        isSelected = account.isSelected,
                        onSelect = { viewModel.selectAccount(account.uuid) },
                        onOpenDetails = { selectedAccountForDetails = account },
                        onOpenSkinManager = { showSkinManagerAccount = account },
                        onRefresh = { viewModel.refreshAccount(account.uuid) },
                        onRename = { accountToRename = account },
                        onRemove = { accountToRemove = account }
                    )
                }
            }

            item {
                Spacer(modifier = Modifier.height(64.dp))
            }
        }
    }

    // Dialog: Add Account Selection
    if (showAddAccountDialog) {
        AddAccountDialog(
            viewModel = viewModel,
            onDismiss = { showAddAccountDialog = false }
        )
    }

    // Dialog: Account Details
    selectedAccountForDetails?.let { account ->
        AccountDetailsDialog(
            account = account,
            isSelected = account.isSelected,
            onSelect = { viewModel.selectAccount(account.uuid) },
            onRefreshAuth = { viewModel.refreshAccount(account.uuid) },
            onRenameProfile = {
                selectedAccountForDetails = null
                accountToRename = account
            },
            onOpenSkinManager = {
                selectedAccountForDetails = null
                showSkinManagerAccount = account
            },
            onRemoveAccount = {
                selectedAccountForDetails = null
                accountToRemove = account
            },
            onDismiss = { selectedAccountForDetails = null }
        )
    }

    // Dialog: Skin Manager (Custom Skin, 3D Preview, Cape)
    showSkinManagerAccount?.let { account ->
        SkinManagerDialog(
            account = account,
            viewModel = viewModel,
            onDismiss = { showSkinManagerAccount = null }
        )
    }

    // Dialog: Rename Account Profile
    accountToRename?.let { account ->
        RenameProfileDialog(
            account = account,
            onDismiss = { accountToRename = null },
            onConfirm = { newName ->
                viewModel.renameAccount(account.uuid, newName)
                accountToRename = null
            }
        )
    }

    // Dialog: Remove Account Confirmation
    accountToRemove?.let { account ->
        AlertDialog(
            onDismissRequest = { accountToRemove = null },
            icon = { Icon(Icons.Default.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error) },
            title = {
                Text(
                    text = if (account.isAuthenticated) "Sign Out Account?" else "Remove Profile?",
                    fontWeight = FontWeight.Bold
                )
            },
            text = {
                Text(
                    text = "Are you sure you want to remove ${account.username}? All cached tokens and local preferences for this account will be cleared."
                )
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.removeAccount(account.uuid)
                        accountToRemove = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.error)
                ) {
                    Text(if (account.isAuthenticated) "Sign Out" else "Remove")
                }
            },
            dismissButton = {
                TextButton(onClick = { accountToRemove = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
private fun AccountStatCard(
    modifier: Modifier = Modifier,
    value: String,
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.65f))
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
            Spacer(modifier = Modifier.height(4.dp))
            Text(value, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold))
            Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun RenameProfileDialog(
    account: AccountEntity,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit
) {
    var nameInput by remember { mutableStateOf(account.username) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Rename Profile", fontWeight = FontWeight.Bold) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    text = "Enter a new username for this profile:",
                    style = MaterialTheme.typography.bodySmall
                )
                OutlinedTextField(
                    value = nameInput,
                    onValueChange = { nameInput = it },
                    label = { Text("Username") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = { onConfirm(nameInput.trim()) },
                enabled = nameInput.isNotBlank()
            ) {
                Text("Save")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
