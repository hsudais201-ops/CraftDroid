package com.example.ui.content

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.content.ContentItem
import com.example.content.ContentType
import com.example.content.ModrinthRepository
import com.example.core.LauncherContainer
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

data class ContentUiState(
    val type: ContentType = ContentType.MOD,
    val items: List<ContentItem> = emptyList(),
    val categories: List<String> = emptyList(),
    val query: String = "",
    val category: String? = null,
    val loading: Boolean = true,
    val refreshing: Boolean = false,
    val loadingMore: Boolean = false,
    val hasMore: Boolean = true,
    val error: String? = null,
    val message: String? = null,
    val installingId: String? = null
)

class ContentBrowserViewModel(private val container: LauncherContainer) : ViewModel() {
    private val repository = ModrinthRepository(container.context)
    private val _state = MutableStateFlow(ContentUiState())
    val state: StateFlow<ContentUiState> = _state.asStateFlow()

    init { refresh() }

    fun selectType(type: ContentType) {
        _state.value = _state.value.copy(type = type, items = emptyList(), loading = true, error = null, category = null, hasMore = true)
        refresh()
    }

    fun setQuery(value: String) {
        _state.value = _state.value.copy(query = value, items = emptyList(), loading = true, error = null, hasMore = true)
        refresh()
    }

    fun setCategory(value: String?) {
        _state.value = _state.value.copy(category = value, items = emptyList(), loading = true, error = null, hasMore = true)
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val current = _state.value
            _state.value = current.copy(loading = current.items.isEmpty(), refreshing = current.items.isNotEmpty(), error = null)
            try {
                val version = container.settingsRepository.settingsFlow.first().selectedVersionId
                val page = withContext(Dispatchers.IO) {
                    repository.search(current.type, current.query, version, current.category, 0)
                }
                val categories = page.items.flatMap { it.categories }.distinct().sorted().take(12)
                _state.value = _state.value.copy(
                    items = page.items,
                    categories = categories,
                    loading = false,
                    refreshing = false,
                    hasMore = page.hasMore,
                    error = null
                )
            } catch (t: Throwable) {
                LauncherLogger.error("Content load failed: " + (t.message ?: t.javaClass.simpleName))
                _state.value = _state.value.copy(loading = false, refreshing = false, error = t.message ?: "Could not load content")
            }
        }
    }

    fun loadMore() {
        val current = _state.value
        if (current.loading || current.loadingMore || !current.hasMore) return
        viewModelScope.launch {
            _state.value = current.copy(loadingMore = true)
            try {
                val version = container.settingsRepository.settingsFlow.first().selectedVersionId
                val page = withContext(Dispatchers.IO) {
                    repository.search(current.type, current.query, version, current.category, current.items.size)
                }
                _state.value = _state.value.copy(
                    items = _state.value.items + page.items,
                    loadingMore = false,
                    hasMore = page.hasMore
                )
            } catch (t: Throwable) {
                _state.value = _state.value.copy(loadingMore = false, error = t.message ?: "Could not load more")
            }
        }
    }

    fun install(item: ContentItem) {
        if (item.isLocal) return
        viewModelScope.launch {
            _state.value = _state.value.copy(installingId = item.id, message = null, error = null)
            try {
                val version = container.settingsRepository.settingsFlow.first().selectedVersionId
                withContext(Dispatchers.IO) { repository.install(item, version) }
                _state.value = _state.value.copy(installingId = null, message = item.name + " installed")
            } catch (t: Throwable) {
                _state.value = _state.value.copy(installingId = null, error = "Install failed: " + (t.message ?: "unknown error"))
            }
        }
    }

    fun clearMessage() {
        _state.value = _state.value.copy(message = null)
    }

    class Factory(private val container: LauncherContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T = ContentBrowserViewModel(container) as T
    }
}
