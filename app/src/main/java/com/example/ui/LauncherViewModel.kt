package com.example.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.example.core.LauncherContainer
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
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

enum class LauncherScreen {
    HOME,
    VERSIONS,
    PROFILES,
    ACCOUNTS,
    SETTINGS,
    LOGS,
    GAME_PLAY,
    CONTENT,
    SERVERS,
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

    fun selectVersion(versionId: String) {
        viewModelScope.launch {
            container.settingsRepository.updateSelectedVersion(versionId)
        }
    }

    fun refreshVersions() {
        viewModelScope.launch { container.versionManager.fetchVersions() }
    }

    fun installSelectedVersion(versionId: String? = null) {
        val current = homeUiState.value
        val vId = versionId?.takeIf { it.isNotBlank() } ?: current.selectedVersionId
        val summary = versions.value.find { it.id == vId }
        val url = summary?.url ?: "https://piston-meta.mojang.com/v1/packages/${vId}/${vId}.json"

        viewModelScope.launch {
            val success = container.installer.installVersion(
                versionId = vId,
                versionJsonUrl = url,
                onProgress = { },
                onStatus = { _downloadStatusText.value = it }
            )
            container.versionManager.fetchVersions()
            if (success && !settings.value.onboardingComplete) {
                container.settingsRepository.updateSelectedVersion(vId)
                container.settingsRepository.completeOnboarding()
                _currentScreen.value = LauncherScreen.HOME
            }
        }
    }

    fun launchMinecraftToServer(host: String, port: Int) {
        val current = homeUiState.value
        val account = current.selectedAccount ?: run {
            _currentScreen.value = LauncherScreen.ACCOUNTS
            return
        }
        container.launchManager.launch(
            versionId = current.selectedVersionId,
            uuid = account.uuid,
            ramMb = current.ramMb,
            rendererBackend = current.rendererBackend,
            customJvmArgs = settings.value.customJvmArgs,
            serverHost = host,
            serverPort = port
        )
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

    fun updateCurseForgeProxyUrl(url: String) {
        viewModelScope.launch { container.settingsRepository.updateCurseForgeProxyUrl(url) }
    }

    fun updateJavaMajorOverride(major: Int?) {
        viewModelScope.launch { container.settingsRepository.updateJavaMajorOverride(major) }
    }

    fun updateJvmArgs(args: String) {
        viewModelScope.launch {
            container.settingsRepository.updateJvmArgs(args)
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

    fun cancelDownload() {
        container.downloadManager.cancel()
    }

    fun installLoader(minecraftVersion: String, loader: String, loaderVersion: String) {
        viewModelScope.launch {
            try {
                when (loader.lowercase()) {
                    "fabric" -> {
                        val result = container.fabricLoaderInstaller.install(minecraftVersion, loaderVersion)
                        if (!result.success) error(result.error ?: "Fabric installation failed")
                    }
                    "forge", "neoforge" -> {
                        val result = container.forgeNeoForgeInstaller.prepare(loader, minecraftVersion, loaderVersion)
                        if (!result.success) error(result.error ?: "Loader installation failed")
                    }
                    "quilt" -> {
                        val result = container.quiltLoaderInstaller.install(minecraftVersion, loaderVersion)
                        if (!result.success) error(result.error ?: "Quilt installation failed")
                    }
                    else -> error("Unsupported loader: $loader")
                }
                _downloadStatusText.value = loader + " " + loaderVersion + " installed"
                container.versionManager.fetchVersions()
            } catch (t: Throwable) {
                _downloadStatusText.value = loader + " installation failed: " + (t.message ?: "unknown error")
                LauncherLogger.error(_downloadStatusText.value)
            }
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
