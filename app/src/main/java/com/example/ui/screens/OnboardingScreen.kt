package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Download
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel
import com.example.ui.theme.UiTokens

@Composable
fun OnboardingScreen(
    viewModel: LauncherViewModel,
    onContinue: () -> Unit = { viewModel.navigateTo(LauncherScreen.VERSIONS) }
) {
    Box(
        Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {
        Card(
            Modifier.fillMaxWidth(0.72f).padding(24.dp),
            shape = UiTokens.CardShape,
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
        ) {
            Column(
                Modifier.padding(28.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Icon(Icons.Default.Download, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Text("Welcome to Droid Launcher", style = MaterialTheme.typography.headlineMedium)
                Text(
                    "Start by installing a Minecraft version. After the first install, your normal launcher home will be available.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(Modifier.height(4.dp))
                Button(onClick = onContinue, modifier = Modifier.fillMaxWidth().height(UiTokens.ButtonMinHeight)) {
                    Text("Choose a Minecraft version")
                }
            }
        }
    }
}
