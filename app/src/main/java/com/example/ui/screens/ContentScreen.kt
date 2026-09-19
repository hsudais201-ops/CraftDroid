package com.example.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.content.ContentProject
import com.example.ui.ContentSource
import com.example.ui.LauncherScreen
import com.example.ui.LauncherViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContentScreen(
    viewModel: LauncherViewModel,
    modifier: Modifier = Modifier
) {
    val state by viewModel.contentBrowser.collectAsState()

    val modrinthTypes = listOf("mod", "modpack", "resourcepack", "shader")
    val curseForgeTypes = listOf("mods", "modpacks", "resource packs", "shaders", "worlds")

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("Content") },
                navigationIcon = {
                    IconButton(onClick = { viewModel.navigateTo(LauncherScreen.HOME) }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = state.source == ContentSource.MODRINTH,
                    onClick = { viewModel.updateContentSource(ContentSource.MODRINTH) },
                    label = { Text("Modrinth") }
                )
                FilterChip(
                    selected = state.source == ContentSource.CURSEFORGE,
                    onClick = { viewModel.updateContentSource(ContentSource.CURSEFORGE) },
                    label = { Text("CurseForge") }
                )
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                (if (state.source == ContentSource.MODRINTH) modrinthTypes else curseForgeTypes).forEach { type ->
                    FilterChip(
                        selected = state.projectType == type,
                        onClick = { viewModel.updateContentType(type) },
                        label = { Text(type.replaceFirstChar { it.uppercase() }) }
                    )
                }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf(
                    null to "Any loader",
                    "forge" to "Forge",
                    "fabric" to "Fabric",
                    "quilt" to "Quilt",
                    "neoforge" to "NeoForge"
                ).forEach { (loader, label) ->
                    FilterChip(
                        selected = state.loader == loader,
                        onClick = { viewModel.updateContentLoader(loader) },
                        label = { Text(label) }
                    )
                }
            }

            OutlinedTextField(
                value = state.query,
                onValueChange = { viewModel.updateContentQuery(it) },
                singleLine = true,
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                placeholder = { Text("Search mods, packs, shaders, resource packs or worlds") },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = { viewModel.searchContent() },
                enabled = !state.isLoading
            ) {
                Text("Search")
            }

            state.error?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium
                )
            }

            if (state.status.isNotBlank()) {
                Text(state.status, style = MaterialTheme.typography.bodySmall)
            }

            if (state.isLoading) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center
                ) {
                    CircularProgressIndicator()
                }
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                if (state.source == ContentSource.MODRINTH) {
                    items(state.modrinthResults, key = { it.id }) { project ->
                        ModrinthProjectRow(project, state.projectType) {
                            viewModel.installContent(project.id, false, state.projectType)
                        }
                    }
                } else {
                    items(state.curseForgeResults, key = { it.id }) { project ->
                        Column(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)
                        ) {
                            Text(project.name, style = MaterialTheme.typography.titleMedium)
                            Text(project.summary, style = MaterialTheme.typography.bodySmall)
                            Spacer(modifier = Modifier.padding(top = 4.dp))
                            Button(
                                onClick = { viewModel.installContent(project.id.toString(), true, state.projectType) }
                            ) {
                                Text("Install")
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ModrinthProjectRow(
    project: ContentProject,
    projectType: String,
    onInstall: () -> Unit
) {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)
    ) {
        Text(project.title, style = MaterialTheme.typography.titleMedium)
        Text(
            project.description ?: project.slug,
            style = MaterialTheme.typography.bodySmall
        )
        Spacer(modifier = Modifier.padding(top = 4.dp))
        Button(onClick = onInstall) {
            Text("Install")
        }
    }
}
