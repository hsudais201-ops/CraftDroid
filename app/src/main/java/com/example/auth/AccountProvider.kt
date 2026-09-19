package com.example.auth

data class ProviderProfile(
    val uuid: String,
    val username: String,
    val skinUrl: String? = null,
    val skinModel: String = "classic",
    val capeUrl: String? = null,
    val providerType: AccountProviderType,
    val isAuthenticated: Boolean
)

/**
 * Common interface for all Minecraft account providers.
 * Supports Microsoft (official Java), Ely.by (official OAuth2), and Local Test Profiles.
 */
interface AccountProvider {
    val providerType: AccountProviderType
    val providerName: String
    val isOfficiallyAuthenticated: Boolean

    suspend fun getAccessToken(uuid: String): String?
    suspend fun refreshSession(uuid: String): Boolean
    suspend fun getProfile(uuid: String): ProviderProfile?
    suspend fun logout(uuid: String)
}
