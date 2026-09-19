package com.example.ui.server

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.core.LauncherContainer
import com.example.launcher.LaunchState
import com.example.server.MinecraftServerPing
import com.example.server.SavedServer
import com.example.server.ServerAvailability
import com.example.server.ServerStatus
import com.example.server.ServerStore
import com.example.ui.LauncherViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.util.UUID

data class ServerBrowserUiState(
    val servers: List<SavedServer> = emptyList(),
    val statuses: Map<String, ServerStatus> = emptyMap(),
    val loading: Boolean = true,
    val error: String? = null
)

class ServerBrowserViewModel(
    private val container: LauncherContainer,
    private val launcher: LauncherViewModel
) : ViewModel() {
    private val store = ServerStore(container.context)
    private val _state = MutableStateFlow(ServerBrowserUiState(servers = store.load()))
    val state: StateFlow<ServerBrowserUiState> = _state.asStateFlow()

    init { refresh() }

    fun refresh() {
        val servers = _state.value.servers
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val results = withContext(Dispatchers.IO) {
                    servers.associate { it.id to MinecraftServerPing.ping(it) }
                }
                _state.value = _state.value.copy(statuses = results, loading = false)
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loading = false, error = t.message ?: "Could not query servers")
            }
        }
    }

    fun add(name: String, host: String, port: Int) {
        val cleanHost = host.trim().removePrefix("[").removeSuffix("]")
        if (cleanHost.isBlank() || port !in 1..65535) {
            _state.value = _state.value.copy(error = "Enter a valid host and port")
            return
        }
        val server = SavedServer(
            id = UUID.randomUUID().toString(),
            name = name.trim().ifBlank { cleanHost },
            host = cleanHost,
            port = port
        )
        val next = _state.value.servers + server
        store.save(next)
        _state.value = _state.value.copy(servers = next, error = null)
        refresh()
    }

    fun remove(server: SavedServer) {
        val next = _state.value.servers.filterNot { it.id == server.id }
        store.save(next)
        _state.value = _state.value.copy(servers = next, statuses = _state.value.statuses - server.id)
    }

    fun ping(server: SavedServer) {
        viewModelScope.launch {
            val result = withContext(Dispatchers.IO) { MinecraftServerPing.ping(server) }
            _state.value = _state.value.copy(statuses = _state.value.statuses + (server.id to result))
        }
    }

    fun join(server: SavedServer) {
        viewModelScope.launch {
            val settings = container.settingsRepository.settingsFlow.first()
            if (!container.fileSystem.getVersionJarFile(settings.selectedVersionId).isFile) {
                _state.value = _state.value.copy(error = "Install Minecraft " + settings.selectedVersionId + " before joining a server.")
                return@launch
            }
            launcher.launchMinecraftToServer(server.host, server.port)
        }
    }

    class Factory(
        private val container: LauncherContainer,
        private val launcher: LauncherViewModel
    ) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            ServerBrowserViewModel(container, launcher) as T
    }
}
