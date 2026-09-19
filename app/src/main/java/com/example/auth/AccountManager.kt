package com.example.auth

import com.example.core.db.AccountDao
import com.example.core.db.AccountEntity
import com.example.logs.LauncherLogger
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Central manager for all Minecraft launcher accounts.
 * Coordinates Microsoft, Ely.by, and Offline/Local providers without duplicating logic.
 */
class AccountManager(
    private val accountDao: AccountDao,
    private val secureStorage: SecureAccountStorage,
    val microsoftProvider: MicrosoftAccountProvider,
    val elyByProvider: ElyByAccountProvider,
    val localTestProvider: LocalTestProfileProvider,
    private val msAuth: MicrosoftAuthManager,
    private val mcAuth: MinecraftAuthManager,
    private val appScope: CoroutineScope
) {
    val allAccounts = accountDao.getAllAccounts()
    val selectedAccount = accountDao.getSelectedAccountFlow()

    private val _authState = MutableStateFlow<AuthState>(AuthState.Idle)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    private var loginJob: Job? = null

    init {
        // Startup check: load selected account and refresh session if needed
        appScope.launch(Dispatchers.IO) {
            checkAndRefreshStartupAccount()
        }
    }

    fun getProvider(type: AccountProviderType): AccountProvider {
        return when (type) {
            AccountProviderType.MICROSOFT -> microsoftProvider
            AccountProviderType.ELY_BY -> elyByProvider
            AccountProviderType.LOCAL_TEST -> localTestProvider
        }
    }

    suspend fun getAccountByUuid(uuid: String): AccountEntity? = withContext(Dispatchers.IO) {
        accountDao.getAccountByUuid(uuid)
    }

    /**
     * Checks the selected account on launcher startup and refreshes if necessary.
     */
    suspend fun checkAndRefreshStartupAccount() = withContext(Dispatchers.IO) {
        val selected = accountDao.getSelectedAccount() ?: return@withContext
        LauncherLogger.info("Verifying session for active account: ${selected.username} (${selected.providerType})")
        val providerType = AccountProviderType.fromId(selected.providerType)
        if (providerType.isOfficiallyAuthenticated) {
            // Check if token expires within 5 minutes (300000ms)
            if (selected.tokenExpiresAt > 0 && System.currentTimeMillis() >= selected.tokenExpiresAt - 300000) {
                LauncherLogger.info("Session token for ${selected.username} is expiring, refreshing...")
                refreshAccountSession(selected.uuid)
            }
        }
    }

    fun startMicrosoftLogin() {
        loginJob?.cancel()
        loginJob = appScope.launch {
            try {
                _authState.value = AuthState.Authenticating("Connecting to Microsoft...")
                val deviceCode = msAuth.requestDeviceCode()

                _authState.value = AuthState.DeviceCodePrompt(
                    userCode = deviceCode.userCode,
                    verificationUri = deviceCode.verificationUri,
                    message = deviceCode.message
                )

                val tokenResponse = msAuth.pollForToken(
                    deviceCode = deviceCode.deviceCode,
                    intervalSeconds = deviceCode.interval,
                    expiresInSeconds = deviceCode.expiresIn
                ) { status ->
                    _authState.value = AuthState.Polling(status)
                }

                _authState.value = AuthState.Authenticating("Verifying Minecraft Java license...")
                val mcResult = mcAuth.authenticateWithMicrosoft(tokenResponse.accessToken)

                // Save securely
                secureStorage.saveMicrosoftRefreshToken(mcResult.uuid, tokenResponse.refreshToken)
                val expiresAt = System.currentTimeMillis() + (mcResult.expiresIn * 1000L)
                secureStorage.saveMinecraftAccessToken(mcResult.uuid, mcResult.accessToken, expiresAt)

                accountDao.clearSelected()
                val entity = AccountEntity(
                    uuid = mcResult.uuid,
                    username = mcResult.username,
                    userHash = mcResult.userHash,
                    tokenExpiresAt = expiresAt,
                    skinUrl = mcResult.skinUrl,
                    skinModel = "classic",
                    capeUrl = null,
                    isSelected = true,
                    isLocalTestProfile = false,
                    providerType = AccountProviderType.MICROSOFT.id,
                    isAuthenticated = true,
                    avatarType = "Default",
                    createdAt = System.currentTimeMillis(),
                    lastUsedAt = System.currentTimeMillis()
                )
                accountDao.insertAccount(entity)

                LauncherLogger.info("Account ${mcResult.username} successfully added and active.")
                _authState.value = AuthState.Success(mcResult.username, mcResult.uuid)
            } catch (e: Exception) {
                LauncherLogger.error("Microsoft login failed: ${e.message}")
                _authState.value = AuthState.Error(e.message ?: "Authentication failed")
            }
        }
    }

    fun loginWithElyBy(
        codeOrToken: String,
        clientId: String = ElyByAccountProvider.DEFAULT_CLIENT_ID,
        clientSecret: String = "",
        redirectUri: String = ElyByAccountProvider.DEFAULT_REDIRECT_URI
    ) {
        loginJob?.cancel()
        loginJob = appScope.launch {
            try {
                _authState.value = AuthState.Authenticating("Connecting to Ely.by...")
                val entity = elyByProvider.authenticateWithCodeOrToken(codeOrToken, clientId, clientSecret, redirectUri)
                _authState.value = AuthState.Success(entity.username, entity.uuid)
            } catch (e: Exception) {
                LauncherLogger.error("Ely.by login failed: ${e.message}")
                _authState.value = AuthState.Error(e.message ?: "Ely.by authentication failed")
            }
        }
    }

    fun cancelLogin() {
        loginJob?.cancel()
        _authState.value = AuthState.Idle
    }

    fun resetAuthState() {
        _authState.value = AuthState.Idle
    }

    /** UI-safe reporting hooks for local profile operations. */
    fun reportAuthSuccess(username: String, uuid: String) {
        _authState.value = AuthState.Success(username, uuid)
    }

    fun reportAuthError(message: String) {
        _authState.value = AuthState.Error(message)
    }

    suspend fun selectAccount(uuid: String) = withContext(Dispatchers.IO) {
        accountDao.clearSelected()
        accountDao.setSelected(uuid)
        accountDao.updateLastUsed(uuid)
        LauncherLogger.info("Switched active Minecraft account to UUID: $uuid")
    }

    suspend fun removeAccount(uuid: String) = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid)
        if (account != null) {
            val provider = getProvider(AccountProviderType.fromId(account.providerType))
            provider.logout(uuid)
        }
        secureStorage.clearTokens(uuid)
        accountDao.deleteAccountByUuid(uuid)
        LauncherLogger.info("Removed account UUID: $uuid")
    }

    suspend fun refreshAccountSession(uuid: String): Boolean = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid) ?: return@withContext false
        val provider = getProvider(AccountProviderType.fromId(account.providerType))
        provider.refreshSession(uuid)
    }

    suspend fun createLocalTestProfile(
        username: String,
        testUuid: String? = null,
        avatar: String,
        skinUrl: String? = null,
        skinModel: String = "classic"
    ): AccountEntity = withContext(Dispatchers.IO) {
        localTestProvider.createProfile(
            username = username,
            customUuid = testUuid,
            avatarType = avatar,
            skinUrl = skinUrl,
            skinModel = skinModel
        )
    }

    suspend fun updateLocalTestProfile(
        uuid: String,
        username: String,
        avatar: String,
        skinUrl: String? = null,
        skinModel: String? = null
    ) = withContext(Dispatchers.IO) {
        val existing = accountDao.getAccountByUuid(uuid) ?: return@withContext
        if (existing.isLocalTestProfile) {
            val normalized = username.trim().ifBlank { "Player" }
            require(normalized.length in 3..16) { "Offline username must be 3–16 characters." }
            require(normalized.matches(Regex("[A-Za-z0-9_]+"))) { "Offline username can only contain letters, numbers, and underscores." }
            accountDao.insertAccount(
                existing.copy(
                    username = normalized,
                    avatarType = avatar,
                    skinUrl = skinUrl ?: existing.skinUrl,
                    skinModel = skinModel ?: existing.skinModel,
                    lastUsedAt = System.currentTimeMillis()
                )
            )
            LauncherLogger.info("Updated Offline / Local Profile: $uuid")
        }
    }

    suspend fun renameAccount(uuid: String, newName: String) = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid) ?: return@withContext
        if (account.isLocalTestProfile) {
            localTestProvider.renameProfile(uuid, newName)
        } else {
            accountDao.updateUsername(uuid, newName)
        }
    }

    suspend fun updateAccountSkin(
        uuid: String,
        skinUrl: String?,
        skinModel: String = "classic"
    ) = withContext(Dispatchers.IO) {
        val existing = accountDao.getAccountByUuid(uuid) ?: return@withContext
        accountDao.insertAccount(
            existing.copy(
                skinUrl = skinUrl,
                skinModel = skinModel,
                lastUsedAt = System.currentTimeMillis()
            )
        )
        LauncherLogger.info("Updated skin for account ${existing.username} ($uuid) -> model=$skinModel")
    }

    suspend fun getValidAccessToken(uuid: String): String? = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid) ?: return@withContext null
        val provider = getProvider(AccountProviderType.fromId(account.providerType))
        provider.getAccessToken(uuid)
    }

    /**
     * Launch validation:
     * - MICROSOFT: legitimate token verification, auto-refreshed if needed.
     * - ELY_BY: legitimate Ely.by OAuth2 token verification.
     * - LOCAL_TEST: Pojav-style local/offline profile; never produces fake tokens or claims online authentication.
     */
    suspend fun validateAccountForLaunch(uuid: String, allowLocalTestMode: Boolean = true): Result<AccountEntity> = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid)
            ?: return@withContext Result.failure(IllegalStateException("Selected account not found."))

        when (AccountProviderType.fromId(account.providerType)) {
            AccountProviderType.MICROSOFT -> {
                val token = microsoftProvider.getAccessToken(uuid)
                if (token.isNullOrBlank()) {
                    Result.failure(IllegalStateException("Your Microsoft session has expired. Please sign in again."))
                } else {
                    try {
                        // A cached token can still be structurally valid while no longer
                        // representing the selected Minecraft profile. Verify the profile
                        // before constructing the game command line.
                        val profile = mcAuth.validateSession(token, account.uuid)
                        val refreshedAccount = account.copy(
                            username = profile.username,
                            skinUrl = profile.skinUrl ?: account.skinUrl,
                            tokenExpiresAt = secureStorage.getMinecraftAccessTokenExpiry(uuid)
                                ?: account.tokenExpiresAt,
                            isAuthenticated = true,
                            lastUsedAt = System.currentTimeMillis()
                        )
                        accountDao.insertAccount(refreshedAccount)
                        Result.success(refreshedAccount)
                    } catch (e: Exception) {
                        LauncherLogger.warn("Microsoft session validation failed for ${account.username}: ${e.message}")
                        Result.failure(IllegalStateException("Microsoft Minecraft session is no longer valid. Please sign in again."))
                    }
                }
            }
            AccountProviderType.ELY_BY -> {
                val token = elyByProvider.getAccessToken(uuid)
                if (token.isNullOrBlank()) {
                    Result.failure(IllegalStateException("Your Ely.by session has expired. Please sign in again."))
                } else {
                    accountDao.updateLastUsed(uuid)
                    Result.success(account)
                }
            }
            AccountProviderType.LOCAL_TEST -> {
                // Local/offline accounts intentionally do not require an online token.
                // This is equivalent to an offline/local launcher profile, not a forged
                // Microsoft session or ownership token.
                accountDao.updateLastUsed(uuid)
                Result.success(account)
            }
        }
    }
}
