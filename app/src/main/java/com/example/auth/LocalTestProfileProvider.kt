package com.example.auth

import com.example.core.db.AccountDao
import com.example.core.db.AccountEntity
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.UUID
import java.nio.charset.StandardCharsets

/**
 * Provider for offline/local profiles.
 * These profiles are local-only and are not authenticated Minecraft accounts.
 * Never produces fake tokens, never claims ownership of Minecraft,
 * and is explicitly marked as unauthenticated.
 */
class LocalTestProfileProvider(
    private val accountDao: AccountDao
) : AccountProvider {

    override val providerType: AccountProviderType = AccountProviderType.LOCAL_TEST
    override val providerName: String = "Offline / Local"
    override val isOfficiallyAuthenticated: Boolean = false

    /**
     * Local test profiles never produce or generate access tokens.
     */
    override suspend fun getAccessToken(uuid: String): String? {
        return null
    }

    override suspend fun refreshSession(uuid: String): Boolean {
        // No remote session to refresh
        return true
    }

    suspend fun createProfile(
        username: String,
        customUuid: String? = null,
        avatarType: String = "Default",
        skinUrl: String? = null,
        skinModel: String = "classic"
    ): AccountEntity = withContext(Dispatchers.IO) {
        // Validate before touching the current selection. Invalid input must never
        // leave the launcher without an active account.
        val normalizedUsername = username.trim().ifBlank { "Player" }
        require(normalizedUsername.length in 3..16) { "Offline username must be 3–16 characters." }
        require(normalizedUsername.matches(Regex("[A-Za-z0-9_]+"))) { "Offline username can only contain letters, numbers, and underscores." }

        // Stable offline UUID: the same username maps to the same local profile identity.
        val assignedUuid = customUuid?.trim()?.ifBlank { null }
            ?: UUID.nameUUIDFromBytes("OfflinePlayer:$normalizedUsername".toByteArray(StandardCharsets.UTF_8)).toString()
        val isCanonicalUuid = runCatching { UUID.fromString(assignedUuid) }.isSuccess
        val isFixtureId = assignedUuid.startsWith("test-", ignoreCase = true) &&
            assignedUuid.length in 5..64 &&
            assignedUuid.all { it.isLetterOrDigit() || it == '-' || it == '_' }
        require(isCanonicalUuid || isFixtureId) { "Offline account UUID is invalid." }
        val entity = AccountEntity(
            uuid = assignedUuid,
            username = normalizedUsername,
            userHash = "offline_local",
            tokenExpiresAt = 0L,
            skinUrl = skinUrl,
            skinModel = skinModel,
            capeUrl = null,
            isSelected = true,
            isLocalTestProfile = true,
            providerType = AccountProviderType.LOCAL_TEST.id,
            isAuthenticated = false,
            avatarType = avatarType,
            createdAt = System.currentTimeMillis(),
            lastUsedAt = System.currentTimeMillis()
        )
        // Only switch the active account after the new entity is fully constructed.
        // This prevents a failed insert/validation from leaving the launcher with no selection.
        accountDao.insertAccount(entity)
        accountDao.clearSelected()
        accountDao.setSelected(assignedUuid)
        LauncherLogger.info("Created Offline / Local Account: ${entity.username} ($assignedUuid) — no online authentication")
        entity
    }

    suspend fun renameProfile(uuid: String, newUsername: String) = withContext(Dispatchers.IO) {
        val existing = accountDao.getAccountByUuid(uuid) ?: return@withContext
        if (existing.isLocalTestProfile) {
            val normalized = newUsername.trim().ifBlank { "Player" }
            require(normalized.length in 3..16) { "Offline username must be 3–16 characters." }
            require(normalized.matches(Regex("[A-Za-z0-9_]+"))) { "Offline username can only contain letters, numbers, and underscores." }
            accountDao.insertAccount(
                existing.copy(
                    username = normalized,
                    lastUsedAt = System.currentTimeMillis()
                )
            )
            LauncherLogger.info("Renamed offline/local account $uuid to $normalized")
        }
    }

    override suspend fun getProfile(uuid: String): ProviderProfile? = withContext(Dispatchers.IO) {
        val account = accountDao.getAccountByUuid(uuid) ?: return@withContext null
        ProviderProfile(
            uuid = account.uuid,
            username = account.username,
            skinUrl = account.skinUrl,
            skinModel = account.skinModel,
            capeUrl = null,
            providerType = AccountProviderType.LOCAL_TEST,
            isAuthenticated = false
        )
    }

    override suspend fun logout(uuid: String) = withContext(Dispatchers.IO) {
        // Nothing remote to clear
        LauncherLogger.info("Closed offline/local account $uuid")
    }
}
