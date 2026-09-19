package com.example.ui.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.versions.VersionRepairStatus

@Composable
fun RepairDialog(
    versionId: String,
    status: VersionRepairStatus?,
    onRepair: () -> Unit,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        icon = {
            Icon(
                imageVector = Icons.Default.Build,
                contentDescription = null,
                tint = Color(0xFFF57C00),
                modifier = Modifier.size(32.dp)
            )
        },
        title = {
            Text("Verify & Repair Minecraft $versionId")
        },
        text = {
            if (status == null) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(24.dp))
                    Spacer(modifier = Modifier.width(12.dp))
                    Text("Analyzing files & hashes...")
                }
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    CheckItem("Version JSON metadata", status.isJsonValid)
                    CheckItem("Client JAR package", status.isJarValid)
                    CheckItem(
                        "Libraries (${status.totalLibraries - status.missingLibraries}/${status.totalLibraries})",
                        status.missingLibraries == 0
                    )
                    CheckItem(
                        "Asset Objects (${status.totalAssets - status.missingAssets}/${status.totalAssets})",
                        status.missingAssets == 0
                    )
                    CheckItem("Java Runtime ready", status.isJavaInstalled)

                    Spacer(modifier = Modifier.height(6.dp))
                    if (status.canLaunch) {
                        Text(
                            text = "All essential files are intact. Game is ready to launch.",
                            color = Color(0xFF2E7D32),
                            style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold)
                        )
                    } else {
                        Text(
                            text = "Found missing or corrupted files. Repair will automatically re-download them.",
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = onRepair,
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFF57C00))
            ) {
                Text("REPAIR INSTALLATION")
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("Close")
            }
        }
    )
}

@Composable
private fun CheckItem(title: String, isOk: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = title, style = MaterialTheme.typography.bodyMedium)
        if (isOk) {
            Icon(imageVector = Icons.Default.Check, contentDescription = "OK", tint = Color(0xFF2E7D32), modifier = Modifier.size(18.dp))
        } else {
            Icon(imageVector = Icons.Default.Close, contentDescription = "Missing", tint = Color(0xFFD32F2F), modifier = Modifier.size(18.dp))
        }
    }
}
