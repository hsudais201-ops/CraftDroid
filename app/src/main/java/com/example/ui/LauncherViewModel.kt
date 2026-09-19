package com.example.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.core.LauncherContainer
import com.example.content.ContentProject
import com.example.content.CurseForgeCategory
import com.example.content.CurseForgeSearchResult
import com.example.core.db.AccountEntity
import com.example.core.db.ProfileEntity
import com.example.downloader.DownloadProgress
import com.example.input.VirtualButtonType
import com.example.launcher.LaunchState
import com.example.logs.CrashAnalysis
import com.example.logs.LauncherLogger
import com.example.renderer.RendererBackend
import com.example.settings.LauncherSettings
import com.example.versions.VersionRepairStatus
import com.example.versions.VersionSummary
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

enum class ContentSource { MODRINTH, CURSEFORGE }

data class ContentBrowserState(
    val source: ContentSource = ContentSource.MODRINTH,
    val projectType: String = "mod",
    val loader: String? = null,
    val query: String = "",
    val modrinthResults: List<ContentProject> = emptyList(),
    val curseForgeResults: List<CurseForgeSearchResult> = emptyList(),
    val curseForgeCategories: List<CurseForgeCategory> = emptyList(),
    val isLoading: Boolean = false,
    val error: String? = null,
    val status: String = ""
)

enum class LauncherScreen {
    HOME,
    VERSIONS,
    CONTENT,
    PROFILES,
    ACCOUNTS,
    SETTINGS,
    LOGS,
    GAME_PLAY,
    CUSTOMIZE_CONTROLS
}

data class HomeUiState(
    val selectedAccount: AccountEntity? = null,
    val selectedVersionId: String = "1.21.4",
    val isInstalled: Boolean = false,
    val javaVersionRequirement: Int = 21,
    val ramMb: Int = 2048,
    val rendererBackend: RendererBackend = RendererBackend.AUTO,
    val isDownloading: Boolean = false,
    val downloadProgress: DownloadProgress = DownloadProgress(),
    val downloadStatusText: String = "",
    val availableStorage: String = "",
    val repairStatus: VersionRepairStatus? = null,
    val showRepairDialog: Boolean = false
)

class LauncherViewModel(val container: LauncherContainer) : ViewModel() {

    private val _currentScreen = MutableStateFlow(LauncherScreen.HOME)
    val currentScreen: StateFlow<LauncherScreen> = _currentScreen.asStateFlow()

    private val _downloadStatusText = MutableStateFlow("")
    val downloadStatusText: StateFlow<String> = _downloadStatusText.asStateFlow()

    private val _repairStatus = MutableStateFlow<VersionRepairStatus?>(null)
    val repairStatus: StateFlow<VersionRepairStatus?> = _repairStatus.asStateFlow()

    private val _showRepairDialog = MutableStateFlow(false)
    val showRepairDialog: StateFlow<Boolean> = _showRepairDialog.asStateFlow()

    private val _showAuthRequiredDialog = MutableStateFlow(false)
    val showAuthRequiredDialog: StateFlow<Boolean> = _showAuthRequiredDialog.asStateFlow()

    val settings: StateFlow<LauncherSettings> = container.settingsRepository.settingsFlow
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), LauncherSettings())

    val accounts: StateFlow<List<AccountEntity>> = container.accountManager.allAccounts
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val selectedAccount: StateFlow<AccountEntity?> = container.accountManager.selectedAccount
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), null)

    val profiles: StateFlow<List<ProfileEntity>> = container.profileManager.profiles
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val versions: StateFlow<List<VersionSummary>> = container.versionManager.versionsList
    val isVersionsLoading: StateFlow<Boolean> = container.versionManager.isLoading
    val downloadProgress: StateFlow<DownloadProgress> = container.downloadManager.progress
    val launchState: StateFlow<LaunchState> = container.launchManager.state
    val authState = container.accountManager.authState
    val runtimes = container.javaManager.runtimes
    val logs = LauncherLogger.logs
    private val _contentBrowser = MutableStateFlow(ContentBrowserState())
    val contentBrowser: StateFlow<ContentBrowserState> = _contentBrowser.asStateFlow()

    val homeUiState: StateFlow<HomeUiState> = combine(
        selectedAccount,
        settings,
        versions,
        downloadProgress,
        _downloadStatusText,
        _repairStatus,
        _showRepairDialog
    ) { args: Array<Any?> ->
        val account = args[0] as? com.example.core.db.AccountEntity
        val setts = args[1] as com.example.settings.LauncherSettings
        @Suppress("UNCHECKED_CAST")
        val vers = args[2] as List<com.example.versions.VersionSummary>
        val dlProg = args[3] as com.example.downloader.DownloadProgress
        val dlStatus = args[4] as String
        val repStat = args[5] as? com.example.versions.VersionRepairStatus
        val showRep = args[6] as Boolean

        val vId = setts.selectedVersionId
        val versionSummary = vers.find { it.id == vId }
        val isInstalled = versionSummary?.isInstalled ?: container.fileSystem.getVersionJarFile(vId).exists()
        val javaReq = versionSummary?.javaRequirement ?: 21

        HomeUiState(
            selectedAccount = account,
            selectedVersionId = vId,
            isInstalled = isInstalled,
            javaVersionRequirement = javaReq,
            ramMb = setts.ramMb,
            rendererBackend = setts.renderer,
            isDownloading = dlProg.isRunning,
            downloadProgress = dlProg,
            downloadStatusText = dlStatus,
            availableStorage = container.fileSystem.formatBytes(container.fileSystem.getAvailableStorageBytes()),
            repairStatus = repStat,
            showRepairDialog = showRep
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), HomeUiState())

    init {
        viewModelScope.launch {
            container.profileManager.initDefaultProfilesIfNeeded()
            container.versionManager.fetchVersions()
            container.javaManager.refreshRuntimes()
            // Load saved custom button layout
            container.settingsRepository.settingsFlow.collect { setts ->
                if (setts.customButtonLayout.isNotBlank()) {
                    container.touchInputManager.applySerializedPositions(setts.customButtonLayout)
                }
            }
        }
    }

    fun navigateTo(screen: LauncherScreen) {
        _currentScreen.value = screen
    }

    fun updateContentQuery(query: String) {
        _contentBrowser.value = _contentBrowser.value.copy(query = query, error = null)
    }

    fun updateContentType(type: String) {
        _contentBrowser.value = _contentBrowser.value.copy(projectType = type, error = null)
    }

    fun updateContentLoader(loader: String?) {
        _contentBrowser.value = _contentBrowser.value.copy(loader = loader, error = null)
    }

    private fun curseForgeLoaderType(loader: String?): Int? = when (loader?.lowercase()) {
        "forge" -> 1
        "fabric" -> 4
        "quilt" -> 5
        "neoforge" -> 6
        else -> null
    }

    fun updateContentSource(source: ContentSource) {
        _contentBrowser.value = _contentBrowser.value.copy(
            source = source,
            projectType = if (source == ContentSource.MODRINTH) "mod" else "mods",
            error = null,
            modrinthResults = emptyList(),
            curseForgeResults = emptyList()
        )
    }

    fun searchContent() {
        val request = _contentBrowser.value
        viewModelScope.launch {
            _contentBrowser.value = request.copy(isLoading = true, error = null, status = "")
            try {
                val gameVersion = settings.value.selectedVersionId
                if (request.source == ContentSource.MODRINTH) {
                    val results = container.modrinthClient.search(
                        query = request.query,
                        gameVersion = gameVersion,
                        projectType = request.projectType,
                        loader = request.loader
                    )
                    _contentBrowser.value = request.copy(
                        isLoading = false,
                        modrinthResults = results,
                        curseForgeResults = emptyList(),
                        status = "Found " + results.size + " Modrinth projects"
                    )
                } else {
                    val categories = container.curseForgeClient.categoryList()
                    val wanted = categories.filter { cat ->
                        when (request.projectType.lowercase()) {
                            "worlds" -> cat.name.contains("world", true) || cat.name.contains("map", true)
                            "mods" -> cat.name.equals("Mods", true)
                            "resource packs" -> cat.name.contains("resource", true)
                            "shaders" -> cat.name.contains("shader", true)
                            "modpacks" -> cat.name.contains("modpack", true)
                            else -> false
                        }
                    }
                    val categoryIds = wanted.map { it.id }
                    val results = container.curseForgeClient.search(
                        query = request.query,
                        gameVersion = gameVersion,
                        loaderType = curseForgeLoaderType(request.loader),
                        categoryIds = categoryIds
                    )
                    _contentBrowser.value = request.copy(
                        isLoading = false,
                        curseForgeResults = results,
                        modrinthResults = emptyList(),
                        curseForgeCategories = categories,
                        status = "Found " + results.size + " CurseForge projects"
                    )
                }
            } catch (e: Exception) {
                _contentBrowser.value = request.copy(isLoading = false, error = e.message ?: "Content search failed")
            }
        }
    }

    fun installContent(projectId: String, isCurseForge: Boolean, projectType: String) {
        viewModelScope.launch {
            _contentBrowser.value = _contentBrowser.value.copy(isLoading = true, error = null, status = "Resolving compatible files…")
            try {
                val gameVersion = settings.value.selectedVersionId
                if (!isCurseForge) {
                    val destination = when (projectType) {
                        "resourcepack" -> container.fileSystem.resourcePacksDir
                        "shader" -> container.fileSystem.shaderPacksDir
                        else -> container.fileSystem.modsDir
                    }
                    container.contentInstallManager.installModrinthVersion(
                        projectId = projectId,
                        minecraftVersion = gameVersion,
                        loader = request.loader,
                        destinationDir = destination
                    )
                } else {
                    val file = container.curseForgeClient.latestCompatibleFile(
                        modId = projectId.toLong(),
                        gameVersion = gameVersion,
                        loaderType = curseForgeLoaderType(request.loader)
                    )
                    when (projectType.lowercase()) {
                        "worlds" -> container.contentInstallManager.installCurseForgeWorld(projectId.toLong(), file.id)
                        "modpacks" -> {
                            val archive = java.io.File(container.fileSystem.runtimeDir, "downloads/cf-pack-" + file.id + ".zip")
                            archive.parentFile?.mkdirs()
                            if (!container.downloadManager.downloadSingleFile(
                                    com.example.downloader.DownloadTask(
                                        url = container.curseForgeClient.distributionUrl(projectId.toLong(), file.id),
                                        destination = archive,
                                        size = file.fileLength,
                                        name = file.fileName
                                    )
                                )
                            ) throw java.io.IOException("CurseForge modpack archive download failed")
                            container.contentInstallManager.installCurseForgeModpack(archive, java.io.File(container.fileSystem.rootDir, "profiles/" + projectId))
                            archive.delete()
                        }
                        "resource packs" -> container.contentInstallManager.installCurseForgeFile(
                            projectId.toLong(), file.id, container.fileSystem.resourcePacksDir, gameVersion, curseForgeLoaderType(request.loader)
                        )
                        "shaders" -> container.contentInstallManager.installCurseForgeFile(
                            projectId.toLong(), file.id, container.fileSystem.shaderPacksDir, gameVersion, curseForgeLoaderType(request.loader)
                        )
                        else -> container.contentInstallManager.installCurseForgeFile(
                            projectId.toLong(), file.id, container.fileSystem.modsDir, gameVersion, curseForgeLoaderType(request.loader)
                        )
                    }
                }
                _contentBrowser.value = _contentBrowser.value.copy(isLoading = false, status = "Install completed successfully")
            } catch (e: Exception) {
                _contentBrowser.value = _contentBrowser.value.copy(isLoading = false, error = e.message ?: "Content install failed", status = "")
            }
        }
    }

    fun selectVersion(versionId: String) {
        viewModelScope.launch {
            container.settingsRepository.updateSelectedVersion(versionId)
        }
    }

    fun refreshVersions() {
        viewModelScope.launch {
            try {
                _downloadStatusText.value = "Refreshing Minecraft versions…"
                container.versionManager.fetchVersions()
                _downloadStatusText.value = ""
            } catch (e: Exception) {
                LauncherLogger.error("Version refresh failed: " + e.message)
                _downloadStatusText.value = "Version refresh failed: " + (e.message ?: "network error")
            }
        }
    }

    fun installSelectedVersion() {
        val current = homeUiState.value
        val vId = current.selectedVersionId
        val summary = versions.value.find { it.id == vId }
        val url = summary?.url ?: run {
            _downloadStatusText.value = "Version metadata is unavailable. Refresh the version list first."
            LauncherLogger.error("Cannot install " + vId + ": version manifest URL is missing")
            return
        }

        viewModelScope.launch {
            try {
                container.installer.installVersion(
                    versionId = vId,
                    versionJsonUrl = url,
                    onProgress = {},
                    onStatus = { _downloadStatusText.value = it }
                )
                container.versionManager.fetchVersions()
            } catch (e: Exception) {
                LauncherLogger.error("Version installation failed for " + vId + ": " + e.message)
                _downloadStatusText.value = "Installation failed: " + (e.message ?: "unknown error")
            }
        }
    }

    fun launchMinecraft() {
        val current = homeUiState.value
        val account = current.selectedAccount
        if (account == null) {
            _currentScreen.value = LauncherScreen.ACCOUNTS
            return
        }

        // Offline / Local profiles are intentionally supported as local launcher sessions.
        // They never receive a forged Microsoft token and remain unable to authenticate
        // to online-mode servers. The launch manager supplies the legacy/offline session.
        container.launchManager.launch(
            versionId = current.selectedVersionId,
            uuid = account.uuid,
            ramMb = current.ramMb,
            rendererBackend = current.rendererBackend,
            customJvmArgs = settings.value.customJvmArgs
        )
    }

    fun dismissAuthRequiredDialog() {
        _showAuthRequiredDialog.value = false
    }

    fun createLocalTestProfile(
        username: String,
        testUuid: String? = null,
        avatar: String = "Default",
        skinUrl: String? = null,
        skinModel: String = "classic"
    ) {
        viewModelScope.launch {
            try {
                val account = container.accountManager.createLocalTestProfile(
                    username = username,
                    testUuid = testUuid,
                    avatar = avatar,
                    skinUrl = skinUrl,
                    skinModel = skinModel
                )
                container.accountManager.reportAuthSuccess(account.username, account.uuid)
            } catch (e: Exception) {
                LauncherLogger.error("Offline/local profile creation failed: ${e.message}")
                container.accountManager.reportAuthError(e.message ?: "Could not create offline account")
            }
        }
    }

    fun updateLocalTestProfile(
        uuid: String,
        username: String,
        avatar: String,
        skinUrl: String? = null,
        skinModel: String? = null
    ) {
        viewModelScope.launch {
            container.accountManager.updateLocalTestProfile(uuid, username, avatar, skinUrl, skinModel)
        }
    }

    fun updateAccountSkin(uuid: String, skinUrl: String?, skinModel: String = "classic") {
        viewModelScope.launch {
            container.accountManager.updateAccountSkin(uuid, skinUrl, skinModel)
        }
    }

    fun updateEnableLocalTestProfiles(enabled: Boolean) {
        viewModelScope.launch {
            container.settingsRepository.updateEnableLocalTestProfiles(enabled)
        }
    }

    fun checkRepair(versionId: String) {
        viewModelScope.launch {
            _showRepairDialog.value = true
            _repairStatus.value = container.versionManager.checkRepairStatus(versionId)
        }
    }

    fun performRepair(versionId: String) {
        viewModelScope.launch {
            container.versionManager.repairVersion(
                versionId = versionId,
                onProgress = {},
                onStatus = { _downloadStatusText.value = it }
            )
            _showRepairDialog.value = false
            container.versionManager.fetchVersions()
        }
    }

    fun dismissRepairDialog() {
        _showRepairDialog.value = false
    }

    fun deleteVersion(versionId: String) {
        viewModelScope.launch {
            container.versionManager.deleteVersion(versionId)
        }
    }

    fun startMicrosoftLogin() {
        container.accountManager.startMicrosoftLogin()
    }

    fun cancelLogin() {
        container.accountManager.cancelLogin()
    }

    fun resetAuthState() {
        container.accountManager.resetAuthState()
    }

    fun loginWithElyBy(
        codeOrToken: String,
        clientId: String = com.example.auth.ElyByAccountProvider.DEFAULT_CLIENT_ID,
        clientSecret: String = "",
        redirectUri: String = com.example.auth.ElyByAccountProvider.DEFAULT_REDIRECT_URI
    ) {
        container.accountManager.loginWithElyBy(codeOrToken, clientId, clientSecret, redirectUri)
    }

    fun selectAccount(uuid: String) {
        viewModelScope.launch {
            container.accountManager.selectAccount(uuid)
        }
    }

    fun refreshAccount(uuid: String) {
        viewModelScope.launch {
            container.accountManager.refreshAccountSession(uuid)
        }
    }

    fun renameAccount(uuid: String, newName: String) {
        viewModelScope.launch {
            try {
                container.accountManager.renameAccount(uuid, newName)
            } catch (e: Exception) {
                LauncherLogger.error("Account rename failed: ${e.message}")
                container.accountManager.reportAuthError(e.message ?: "Could not rename account")
            }
        }
    }

    fun removeAccount(uuid: String) {
        viewModelScope.launch {
            container.accountManager.removeAccount(uuid)
        }
    }

    fun updateRam(ramMb: Int) {
        viewModelScope.launch {
            container.settingsRepository.updateRam(ramMb)
        }
    }

    fun updateRenderer(backend: RendererBackend) {
        viewModelScope.launch {
            container.settingsRepository.updateRenderer(backend)
        }
    }

    fun updateJvmArgs(args: String) {
        viewModelScope.launch {
            container.settingsRepository.updateJvmArgs(args)
        }
    }

    fun updateJavaRuntimeOverride(major: Int?) {
        viewModelScope.launch {
            container.settingsRepository.updateJavaRuntimeOverride(major)
        }
    }

    fun updateControls(opacity: Float, scale: Float, sens: Float, invertY: Boolean, virtualMouse: Boolean) {
        viewModelScope.launch {
            container.settingsRepository.updateControls(opacity, scale, sens, invertY, virtualMouse)
            container.touchInputManager.updateSettings(
                opacity = opacity,
                scale = scale,
                sensitivity = sens,
                invertY = invertY,
                virtualMouse = virtualMouse
            )
        }
    }

    fun updateButtonPosition(type: VirtualButtonType, xPercent: Float, yPercent: Float) {
        container.touchInputManager.updateButtonPosition(type, xPercent, yPercent)
    }

    fun saveCustomButtonLayout() {
        viewModelScope.launch {
            container.touchInputManager.saveActiveProfile()
            val serialized = container.touchInputManager.getSerializedPositions()
            container.settingsRepository.updateCustomButtonLayout(serialized)
        }
    }

    fun resetControlsToDefault() {
        viewModelScope.launch {
            container.touchInputManager.resetCurrentProfileToDefault()
            container.touchInputManager.resetToDefaults()
            container.settingsRepository.updateCustomButtonLayout("")
        }
    }

    fun testJava(major: Int) {
        viewModelScope.launch {
            container.javaManager.testJava(major)
        }
    }

    fun installJava(major: Int) {
        viewModelScope.launch {
            container.javaManager.installRuntime(major) {}
        }
    }

    fun resetLaunchToHome() {
        container.launchManager.resetToHome()
    }

    class Factory(private val container: LauncherContainer) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T {
            return LauncherViewModel(container) as T
        }
    }
}
