package com.example.ui.screens

import android.graphics.BitmapFactory
import android.util.Base64
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.core.LauncherContainer
import com.example.server.ServerAvailability
import com.example.ui.LauncherViewModel
import com.example.ui.server.ServerBrowserViewModel
import com.example.ui.theme.UiTokens

@Composable
fun ServerBrowserScreen(viewModel: LauncherViewModel) {
    val vm: ServerBrowserViewModel = viewModel(
        factory = ServerBrowserViewModel.Factory(LauncherContainer.get(viewModel.container.context), viewModel)
    )
    val state by vm.state.collectAsState()
    var showAdd by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().padding(UiTokens.ScreenPadding)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Servers", style = MaterialTheme.typography.headlineMedium)
                Text("Live Java Edition server status", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = vm::refresh, modifier = Modifier.size(UiTokens.IconButtonSize)) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh")
            }
            Button(onClick = { showAdd = true }, modifier = Modifier.size(width = 150.dp, height = 48.dp)) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(Modifier.width(6.dp))
                Text("Add Server")
            }
        }

        state.error?.let { error ->
            Card(Modifier.fillMaxWidth().padding(vertical = 8.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(error, Modifier.weight(1f), color = MaterialTheme.colorScheme.onErrorContainer)
                    OutlinedButton(onClick = vm::refresh) { Text("Retry") }
                }
            }
        }

        if (state.servers.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("No servers yet. Add an IP address and port to begin.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            LazyColumn(
                Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(UiTokens.CardGap),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(vertical = 12.dp)
            ) {
                items(state.servers, key = { it.id }) { server ->
                    val status = state.statuses[server.id]
                    Card(
                        Modifier.fillMaxWidth(),
                        shape = UiTokens.CardShape,
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                    ) {
                        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                            ServerIcon(status?.iconBase64)
                            Spacer(Modifier.width(12.dp))
                            Column(Modifier.weight(1f)) {
                                Text(server.name, style = MaterialTheme.typography.titleMedium)
                                Text(server.host + ":" + server.port, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                Text(
                                    when (status?.availability) {
                                        ServerAvailability.ONLINE -> status.motd.ifBlank { "Online" }
                                        ServerAvailability.OFFLINE -> "Offline" + (status.error?.let { ": " + it } ?: "")
                                        else -> "Checking server status…"
                                    },
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                if (status?.availability == ServerAvailability.ONLINE) {
                                    Text(
                                        status.playersOnline.toString() + "/" + status.playersMax +
                                            " players  •  " + (status.pingMs?.toString() ?: "—") + " ms" +
                                            (if (status.version.isBlank()) "" else "  •  " + status.version),
                                        style = MaterialTheme.typography.bodySmall
                                    )
                                }
                            }
                            if (status?.availability == ServerAvailability.LOADING || status == null) {
                                CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                            }
                            Button(onClick = { vm.join(server) }, enabled = status?.availability == ServerAvailability.ONLINE || status?.availability == ServerAvailability.OFFLINE) {
                                Text("Join")
                            }
                            IconButton(onClick = { vm.ping(server) }) {
                                Icon(Icons.Default.Refresh, contentDescription = "Ping server")
                            }
                            IconButton(onClick = { vm.remove(server) }) {
                                Icon(Icons.Default.Delete, contentDescription = "Delete server")
                            }
                        }
                    }
                }
            }
        }
    }

    if (showAdd) {
        AddServerDialog(
            onDismiss = { showAdd = false },
            onAdd = { name, host, port -> vm.add(name, host, port); showAdd = false }
        )
    }
}

@Composable
private fun ServerIcon(iconBase64: String?) {
    val bitmap = remember(iconBase64) {
        runCatching {
            val raw = iconBase64?.substringAfter("base64,", iconBase64) ?: return@remember null
            BitmapFactory.decodeByteArray(Base64.decode(raw, Base64.DEFAULT), 0, Base64.decode(raw, Base64.DEFAULT).size)
        }.getOrNull()
    }
    if (bitmap != null) {
        Image(bitmap = bitmap.asImageBitmap(), contentDescription = null, modifier = Modifier.size(64.dp))
    } else {
        Box(Modifier.size(64.dp), contentAlignment = Alignment.Center) {
            Text("MC", style = MaterialTheme.typography.titleMedium)
        }
    }
}

@Composable
private fun AddServerDialog(
    onDismiss: () -> Unit,
    onAdd: (String, String, Int) -> Unit
) {
    var name by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }
    var port by remember { mutableStateOf("25565") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add Server") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Name") }, singleLine = true)
                OutlinedTextField(value = address, onValueChange = { address = it }, label = { Text("IP or hostname") }, singleLine = true)
                OutlinedTextField(value = port, onValueChange = { port = it.filter(Char::isDigit) }, label = { Text("Port") }, singleLine = true)
            }
        },
        confirmButton = {
            Button(
                onClick = { onAdd(name, address, port.toIntOrNull() ?: 0) },
                enabled = address.isNotBlank() && (port.toIntOrNull() ?: 0) in 1..65535
            ) { Text("Save") }
        },
        dismissButton = { OutlinedButton(onClick = onDismiss) { Text("Cancel") } }
    )
}
