package com.example.ui.screens

import android.net.Uri
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.snapshotFlow
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.content.ContentType
import com.example.core.LauncherContainer
import com.example.launcher.MinecraftContentManager
import com.example.ui.LauncherViewModel
import com.example.ui.content.ContentBrowserViewModel
import com.example.ui.theme.UiTokens

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContentBrowserScreen(viewModel: LauncherViewModel) {
    val container = LauncherContainer.get(viewModel.container.context)
    val vm: ContentBrowserViewModel = viewModel(factory = ContentBrowserViewModel.Factory(container))
    val state by vm.state.collectAsState()
    val listState = rememberLazyListState()
    val pullState = rememberPullRefreshState(state.refreshing, vm::refresh)
    var search by remember { mutableStateOf("") }

    val worldPicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri == null) return@rememberLauncherForActivityResult
        val context = viewModel.container.context
        runCatching {
            val temp = java.io.File(context.cacheDir, "world-import-" + System.nanoTime() + ".zip")
            context.contentResolver.openInputStream(uri)?.use { input ->
                temp.outputStream().use { output -> input.copyTo(output) }
            } ?: error("Could not read selected archive")
            MinecraftContentManager.importArchive(context, MinecraftContentManager.Kind.WORLD, temp)
            temp.delete()
            vm.refresh()
            Toast.makeText(context, "World imported", Toast.LENGTH_SHORT).show()
        }.onFailure {
            Toast.makeText(context, "World import failed: " + it.message, Toast.LENGTH_LONG).show()
        }
    }

    LaunchedEffect(listState) {
        snapshotFlow { listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0 }
            .collect { last ->
                if (last >= state.items.lastIndex - 3) vm.loadMore()
            }
    }

    Column(Modifier.fillMaxSize().padding(UiTokens.ScreenPadding)) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Feature Center", style = MaterialTheme.typography.headlineMedium)
                Text("Real Modrinth content and local worlds", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (state.type == ContentType.WORLD) {
                OutlinedButton(onClick = { worldPicker.launch(arrayOf("application/zip", "application/octet-stream")) }) {
                    Icon(Icons.Default.Add, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("Import World")
                }
            }
            IconButton(onClick = vm::refresh, modifier = Modifier.size(UiTokens.IconButtonSize)) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh")
            }
        }

        Spacer(Modifier.height(12.dp))
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(ContentType.entries) { type ->
                FilterChip(
                    selected = state.type == type,
                    onClick = { vm.selectType(type) },
                    label = { Text(type.title) }
                )
            }
        }

        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = search,
                onValueChange = { search = it },
                modifier = Modifier.weight(1f),
                singleLine = true,
                label = { Text("Search") }
            )
            Spacer(Modifier.width(8.dp))
            Button(onClick = { vm.setQuery(search.trim()) }) { Text("Search") }
        }

        if (state.categories.isNotEmpty() && state.type != ContentType.WORLD) {
            Spacer(Modifier.height(8.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                item {
                    FilterChip(
                        selected = state.category == null,
                        onClick = { vm.setCategory(null) },
                        label = { Text("All") }
                    )
                }
                items(state.categories) { category ->
                    FilterChip(
                        selected = state.category == category,
                        onClick = { vm.setCategory(category) },
                        label = { Text(category) }
                    )
                }
            }
        }

        state.error?.let { message ->
            Card(
                Modifier.fillMaxWidth().padding(vertical = 8.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)
            ) {
                Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(message, Modifier.weight(1f), color = MaterialTheme.colorScheme.onErrorContainer)
                    OutlinedButton(onClick = vm::refresh) { Text("Retry") }
                }
            }
        }

        state.message?.let { message ->
            AssistChip(onClick = vm::clearMessage, label = { Text(message) })
        }

        Box(
            modifier = Modifier
                .fillMaxSize()
                .pullRefresh(pullState)
        ) {
            when {
                state.loading && state.items.isEmpty() -> {
                    Column(
                        Modifier.fillMaxSize().padding(top = 30.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        repeat(4) {
                            Card(
                                Modifier.fillMaxWidth().height(82.dp),
                                shape = UiTokens.CardShape,
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                            ) {
                                LinearProgressIndicator(Modifier.fillMaxWidth())
                            }
                        }
                    }
                }
                state.items.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        "Nothing found. Try another search or pull down to refresh.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                else -> {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(vertical = 10.dp),
                        verticalArrangement = Arrangement.spacedBy(UiTokens.CardGap)
                    ) {
                        items(state.items, key = { it.id }) { item ->
                            Card(
                                Modifier.fillMaxWidth(),
                                shape = UiTokens.CardShape,
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
                            ) {
                                Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                    if (!item.iconUrl.isNullOrBlank()) {
                                        AsyncImage(
                                            model = item.iconUrl,
                                            contentDescription = null,
                                            modifier = Modifier.size(68.dp)
                                        )
                                    } else {
                                        Box(Modifier.size(68.dp), contentAlignment = Alignment.Center) {
                                            Icon(Icons.Default.Download, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                        }
                                    }

                                    Spacer(Modifier.width(12.dp))
                                    Column(Modifier.weight(1f)) {
                                        Text(item.name, style = MaterialTheme.typography.titleMedium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                        Text(
                                            item.description.ifBlank { "No description provided." },
                                            maxLines = 2,
                                            overflow = TextOverflow.Ellipsis,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp), modifier = Modifier.padding(top = 6.dp)) {
                                            if (item.versions.isNotEmpty()) {
                                                AssistChip(onClick = {}, label = { Text(item.versions.first()) })
                                            }
                                            item.loaders.take(2).forEach { loader ->
                                                AssistChip(onClick = {}, label = { Text(loader) })
                                            }
                                        }
                                    }

                                    Spacer(Modifier.width(8.dp))
                                    if (item.isLocal) {
                                        AssistChip(onClick = {}, label = { Text("Installed") })
                                    } else {
                                        Button(
                                            onClick = { vm.install(item) },
                                            enabled = state.installingId != item.id,
                                            modifier = Modifier.height(UiTokens.ButtonMinHeight)
                                        ) {
                                            if (state.installingId == item.id) {
                                                CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                                            } else {
                                                Text("Install")
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        if (state.loadingMore) {
                            item {
                                Box(Modifier.fillMaxWidth().padding(18.dp), contentAlignment = Alignment.Center) {
                                    CircularProgressIndicator()
                                }
                            }
                        }
                    }
                }
            }
            PullRefreshIndicator(state.refreshing, pullState, Modifier.align(Alignment.TopCenter))
        }    }
}
