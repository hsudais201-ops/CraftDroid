package com.example.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.widget.Toast
import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.logs.LauncherLogger
import com.example.logs.LogLevel
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LogsScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier
) {
    val logs by viewModel.logs.collectAsState()
    val context = LocalContext.current
    val listState = rememberLazyListState()

    var selectedLevelFilter by remember { mutableStateOf<LogLevel?>(null) }
    var autoScroll by remember { mutableStateOf(true) }

    val filteredLogs = remember(logs, selectedLevelFilter) {
        if (selectedLevelFilter == null) logs
        else logs.filter { it.level == selectedLevelFilter }
    }

    LaunchedEffect(filteredLogs.size, autoScroll) {
        if (autoScroll && filteredLogs.isNotEmpty()) {
            listState.animateScrollToItem(filteredLogs.size - 1)
        }
    }

    Column(modifier = modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("Diagnostics & Logs") },
            navigationIcon = {
                IconButton(onClick = { viewModel.navigateTo(LauncherScreen.HOME) }) {
                    Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                }
            },
            actions = {
                IconButton(
                    onClick = {
                        val text = LauncherLogger.getLogsAsText()
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("Minecraft Launcher Logs", text))
                        Toast.makeText(context, "Logs copied to clipboard", Toast.LENGTH_SHORT).show()
                    }
                ) {
                    Icon(imageVector = Icons.Default.Share, contentDescription = "Copy Logs")
                }
                IconButton(onClick = { LauncherLogger.clear() }) {
                    Icon(imageVector = Icons.Default.Clear, contentDescription = "Clear Logs")
                }
            },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
        )

        // Filters row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            FilterChip(
                selected = selectedLevelFilter == null,
                onClick = { selectedLevelFilter = null },
                label = { Text("ALL") }
            )
            FilterChip(
                selected = selectedLevelFilter == LogLevel.INFO,
                onClick = { selectedLevelFilter = if (selectedLevelFilter == LogLevel.INFO) null else LogLevel.INFO },
                label = { Text("INFO") }
            )
            FilterChip(
                selected = selectedLevelFilter == LogLevel.WARN,
                onClick = { selectedLevelFilter = if (selectedLevelFilter == LogLevel.WARN) null else LogLevel.WARN },
                label = { Text("WARN") }
            )
            FilterChip(
                selected = selectedLevelFilter == LogLevel.ERROR,
                onClick = { selectedLevelFilter = if (selectedLevelFilter == LogLevel.ERROR) null else LogLevel.ERROR },
                label = { Text("ERROR") }
            )
            FilterChip(
                selected = selectedLevelFilter == LogLevel.MINECRAFT,
                onClick = { selectedLevelFilter = if (selectedLevelFilter == LogLevel.MINECRAFT) null else LogLevel.MINECRAFT },
                label = { Text("GAME") }
            )
        }

        // Terminal display
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(8.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0xFF101418))
                .padding(8.dp)
        ) {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize()
            ) {
                items(filteredLogs) { entry ->
                    val color = when (entry.level) {
                        LogLevel.INFO -> Color(0xFFCFD8DC)
                        LogLevel.WARN -> Color(0xFFFFD54F)
                        LogLevel.ERROR -> Color(0xFFEF5350)
                        LogLevel.MINECRAFT -> Color(0xFF81C784)
                        LogLevel.DEBUG -> Color(0xFF90A4AE)
                    }

                    Text(
                        text = entry.format(),
                        color = color,
                        fontFamily = FontFamily.Monospace,
                        fontSize = 11.sp,
                        lineHeight = 15.sp,
                        modifier = Modifier.padding(vertical = 1.dp)
                    )
                }
            }
        }
    }
}
