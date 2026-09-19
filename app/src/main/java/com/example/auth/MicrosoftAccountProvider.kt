package com.example.auth

import com.example.core.db.AccountDao
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MicrosoftAccountProvider(
    private val accountDao: AccountDao,
    private val secureStorage: SecureAccountStorage,
    private val msAuth: MicrosoftAuthManager,
    private val mcAuth: MinecraftAuthManager
) : AccountProvider {

    override val providerType: AccountProviderType = AccountProviderType.MICROSOFT
    override val providerName: String = "Microsoft"
    override val isOfficiallyAuthenticated: Boolean = true

    override suspend fun getAccessToken(uuid: String): String? = withContext(Dispatchers.IO) {
        // 1. Check cached valid token
        val cached = secureStorage.getMinecraftAccessToken(uuid)
        if (cached != null) {
            return@withContext cached
        }

        // 2. Token expired or not cached -> refresh using Microsoft Refresh Token
        val refreshed = refreshSession(uuid)
        if (refreshed) {
            secureStorage.getMinecraftAccessToken(uuid)
        } else {
            null
        }
    }

    override suspend fun refreshSession(uuid: String): Boolean = withContext(Dispatchers.IO) {
        val refreshToken = secureStorage.getMicrosoftRefreshToken(uuid) ?: run {
            LauncherLogger.warn("No Microsoft refresh token found for account $uuid.")
            return@withContext false
        }

        try {
            LauncherLogger.info("Session expired for Microsoft account $uuid. Auto-refreshing...")
            val newMsToken = msAuth.refreshMicrosoftToken(refreshToken)
            val mcResult = mcAuth.authenticateWithMicrosoft(newMsToken.accessToken)

            // Update secure store & DB
            secureStorage.saveMicrosoftRefreshToken(uuid, newMsToken.refreshToken)
            val newExpiresAt = System.currentTimeMillis() + (mcResult.expiresIn * 1000L)
            secureStorage.saveMinecraftAccessToken(uuid, mcResult.accessToken, newExpiresAt)

            val currentAcc = accountDao.getAccountByUuid(uuid)
            if (currentAcc != null) {
                accountDao.insertAccount(
                    currentAcc.copy(
                        username = mcResult.username,
                        tokenExpiresAt = newExpiresAt,
                        skinUrl = mcResult.skinUrl ?: currentAcc.skinUrl,
                        lastUsedAt = System.currentTimeMillis()
                    )
                )
            }
            LauncherLogger.info("Microsoft session successfully refreshed for ${mcResult.username}")
            true
        } catch (e: Exception) {
            LauncherLogger.error("Failed to auto-refresh Microsoft Minecraft session: ${e.message}")
            false
        }
    }

    override suspend fun getProfile(uuid: String): ProviderProfile? = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid) ?: return@withContext null
        ProviderProfile(
            uuid = account.uuid,
            username = account.username,
            skinUrl = account.skinUrl,
            skinModel = account.skinModel,
            capeUrl = account.capeUrl,
            providerType = AccountProviderType.MICROSOFT,
            isAuthenticated = true
        )
    }

    override suspend fun logout(uuid: String) = withContext(Dispatchers.IO) {
        secureStorage.clearTokens(uuid)
        LauncherLogger.info("Logged out Microsoft account $uuid")
    }
}
