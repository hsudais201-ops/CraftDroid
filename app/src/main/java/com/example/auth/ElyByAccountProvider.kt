package com.example.auth

import com.example.core.db.AccountDao
import com.example.core.db.AccountEntity
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException
import java.net.URLEncoder

data class ElyByTokenResponse(
    val accessToken: String,
    val refreshToken: String?,
    val expiresIn: Int
)

data class ElyByProfile(
    val id: Long,
    val uuid: String,
    val username: String,
    val skinUrl: String?,
    val isSlim: Boolean,
    val capeUrl: String?
)

/**
 * Official Ely.by OAuth2 Account Provider.
 * Follows Ely.by's official documented OAuth2 and Account API specifications:
 * - Authorization: https://account.ely.by/oauth2/v1
 * - Token Exchange: https://account.ely.by/api/oauth2/v1/token
 * - User Profile: https://account.ely.by/api/account/v1/info
 */
class ElyByAccountProvider(
    private val okHttpClient: OkHttpClient,
    private val accountDao: AccountDao,
    private val secureStorage: SecureAccountStorage
) : AccountProvider {

    companion object {
        const val DEFAULT_CLIENT_ID = "craftdroid_launcher"
        const val DEFAULT_REDIRECT_URI = "https://account.ely.by/oauth2/code/success"
        const val AUTH_URL = "https://account.ely.by/oauth2/v1"
        const val TOKEN_URL = "https://account.ely.by/api/oauth2/v1/token"
        const val PROFILE_URL = "https://account.ely.by/api/account/v1/info"
        const val DEFAULT_SCOPES = "account_info minecraft_server_session offline_access"
    }

    override val providerType: AccountProviderType = AccountProviderType.ELY_BY
    override val providerName: String = "Ely.by"
    override val isOfficiallyAuthenticated: Boolean = true

    /**
     * Builds the official Ely.by OAuth2 authorization URL to open in browser.
     */
    @JvmStatic
        fun buildAuthorizationUrl(
        clientId: String = DEFAULT_CLIENT_ID,
        redirectUri: String = DEFAULT_REDIRECT_URI
    ): String {
        return "$AUTH_URL?client_id=${URLEncoder.encode(clientId, "UTF-8")}" +
                "&response_type=code" +
                "&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
                "&scope=${URLEncoder.encode(DEFAULT_SCOPES, "UTF-8")}" +
                "&prompt=consent"
    }

    /**
     * Authenticates with an Ely.by Authorization Code or OAuth2 Token directly.
     */
    suspend fun authenticateWithCodeOrToken(
        codeOrToken: String,
        clientId: String = DEFAULT_CLIENT_ID,
        clientSecret: String = "",
        redirectUri: String = DEFAULT_REDIRECT_URI
    ): AccountEntity = withContext(Dispatchers.IO) {
        val trimmed = codeOrToken.trim()
        val tokenResponse = if (trimmed.length > 50 && !trimmed.contains(" ") && !trimmed.startsWith("code_")) {
            // Provided token directly
            ElyByTokenResponse(
                accessToken = trimmed,
                refreshToken = null,
                expiresIn = 86400
            )
        } else {
            // Exchange code via official token endpoint
            exchangeCodeForToken(trimmed, clientId, clientSecret, redirectUri)
        }

        LauncherLogger.info("Retrieving official Ely.by user profile...")
        val profile = fetchUserProfile(tokenResponse.accessToken)

        // Save tokens securely (never logged or exposed)
        val expiresAt = System.currentTimeMillis() + (tokenResponse.expiresIn * 1000L)
        secureStorage.saveElyByAccessToken(profile.uuid, tokenResponse.accessToken, expiresAt)
        if (!tokenResponse.refreshToken.isNullOrBlank()) {
            secureStorage.saveElyByRefreshToken(profile.uuid, tokenResponse.refreshToken)
        }

        accountDao.clearSelected()
        val entity = AccountEntity(
            uuid = profile.uuid,
            username = profile.username,
            userHash = "ely_by_${profile.id}",
            tokenExpiresAt = expiresAt,
            skinUrl = profile.skinUrl,
            skinModel = if (profile.isSlim) "slim" else "classic",
            capeUrl = profile.capeUrl,
            isSelected = true,
            isLocalTestProfile = false,
            providerType = AccountProviderType.ELY_BY.id,
            isAuthenticated = true,
            createdAt = System.currentTimeMillis(),
            lastUsedAt = System.currentTimeMillis()
        )
        accountDao.insertAccount(entity)
        LauncherLogger.info("Ely.by account ${profile.username} authenticated successfully.")
        entity
    }

    /**
     * Exchanges OAuth2 code for tokens using Ely.by's official endpoint.
     */
    suspend fun exchangeCodeForToken(
        code: String,
        clientId: String,
        clientSecret: String,
        redirectUri: String
    ): ElyByTokenResponse = withContext(Dispatchers.IO) {
        val formBuilder = FormBody.Builder()
            .add("grant_type", "authorization_code")
            .add("client_id", clientId)
            .add("redirect_uri", redirectUri)
            .add("code", code)

        if (clientSecret.isNotBlank()) {
            formBuilder.add("client_secret", clientSecret)
        }

        val request = Request.Builder()
            .url(TOKEN_URL)
            .post(formBuilder.build())
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response from Ely.by")

        if (!response.isSuccessful) {
            val errorMsg = try {
                JSONObject(responseBody).optString("message", responseBody)
            } catch (e: Exception) {
                responseBody
            }
            throw IOException("Ely.by authentication failed: $errorMsg")
        }

        val json = JSONObject(responseBody)
        ElyByTokenResponse(
            accessToken = json.getString("access_token"),
            refreshToken = json.optString("refresh_token", null),
            expiresIn = json.optInt("expires_in", 86400)
        )
    }

    /**
     * Fetches user profile from Ely.by's official profile endpoint.
     */
    suspend fun fetchUserProfile(accessToken: String): ElyByProfile = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url(PROFILE_URL)
            .get()
            .header("Authorization", "Bearer $accessToken")
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty profile response from Ely.by")

        if (!response.isSuccessful) {
            throw IOException("Failed to load Ely.by profile (HTTP ${response.code})")
        }

        val json = JSONObject(responseBody)
        val id = json.optLong("id", System.currentTimeMillis())
        val uuid = json.optString("uuid", "").ifBlank {
            // Format standard UUID from Ely.by id if not present
            java.util.UUID.nameUUIDFromBytes("ely_by_$id".toByteArray()).toString()
        }
        val username = json.getString("username")

        var skinUrl: String? = null
        var isSlim = false
        val skinObj = json.optJSONObject("skin")
        if (skinObj != null) {
            skinUrl = skinObj.optString("url", null)
            isSlim = skinObj.optBoolean("isSlim", false)
        }

        var capeUrl: String? = null
        val capeObj = json.optJSONObject("cape")
        if (capeObj != null) {
            capeUrl = capeObj.optString("url", null)
        }

        ElyByProfile(
            id = id,
            uuid = uuid,
            username = username,
            skinUrl = skinUrl,
            isSlim = isSlim,
            capeUrl = capeUrl
        )
    }

    override suspend fun getAccessToken(uuid: String): String? = withContext(Dispatchers.IO) {
        val cached = secureStorage.getElyByAccessToken(uuid)
        if (cached != null) {
            return@withContext cached
        }

        val refreshed = refreshSession(uuid)
        if (refreshed) {
            secureStorage.getElyByAccessToken(uuid)
        } else {
            null
        }
    }

    override suspend fun refreshSession(uuid: String): Boolean = withContext(Dispatchers.IO) {
        val refreshToken = secureStorage.getElyByRefreshToken(uuid) ?: return@withContext false
        try {
            LauncherLogger.info("Refreshing Ely.by session for UUID $uuid...")
            val formBody = FormBody.Builder()
                .add("grant_type", "refresh_token")
                .add("client_id", DEFAULT_CLIENT_ID)
                .add("refresh_token", refreshToken)
                .build()

            val request = Request.Builder()
                .url(TOKEN_URL)
                .post(formBody)
                .header("Accept", "application/json")
                .build()

            val response = okHttpClient.newCall(request).execute()
            val body = response.body?.string() ?: return@withContext false
            if (!response.isSuccessful) {
                LauncherLogger.warn("Ely.by token refresh failed: HTTP ${response.code}")
                return@withContext false
            }

            val json = JSONObject(body)
            val newAccess = json.getString("access_token")
            val newRefresh = json.optString("refresh_token", refreshToken)
            val expiresIn = json.optInt("expires_in", 86400)
            val expiresAt = System.currentTimeMillis() + (expiresIn * 1000L)

            secureStorage.saveElyByAccessToken(uuid, newAccess, expiresAt)
            secureStorage.saveElyByRefreshToken(uuid, newRefresh)

            val account = accountDao.getAccountByUuid(uuid)
            if (account != null) {
                accountDao.insertAccount(
                    account.copy(
                        tokenExpiresAt = expiresAt,
                        lastUsedAt = System.currentTimeMillis()
                    )
                )
            }
            LauncherLogger.info("Ely.by session refreshed successfully for UUID $uuid")
            true
        } catch (e: Exception) {
            LauncherLogger.error("Error refreshing Ely.by session: ${e.message}")
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
            providerType = AccountProviderType.ELY_BY,
            isAuthenticated = true
        )
    }

    override suspend fun logout(uuid: String) = withContext(Dispatchers.IO) {
        secureStorage.clearTokens(uuid)
        LauncherLogger.info("Logged out Ely.by account $uuid")
    }
}
