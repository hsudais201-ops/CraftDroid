package com.example.auth

import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.IOException

class MicrosoftAuthManager(private val okHttpClient: OkHttpClient) {

    companion object {
        // Standard Azure Client ID for Minecraft Authentication
        const val CLIENT_ID = "00000000402b5328"
        const val SCOPE = "XboxLive.signin offline_access"
        private const val DEVICE_CODE_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode"
        private const val TOKEN_URL = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
    }

    suspend fun requestDeviceCode(): DeviceCodeResponse = withContext(Dispatchers.IO) {
        val formBody = FormBody.Builder()
            .add("client_id", CLIENT_ID)
            .add("scope", SCOPE)
            .build()

        val request = Request.Builder()
            .url(DEVICE_CODE_URL)
            .post(formBody)
            .header("Accept", "application/json")
            .build()

        LauncherLogger.info("Requesting Microsoft OAuth device code...")
        val response = okHttpClient.newCall(request).execute()
        val responseBody = response.body?.string() ?: throw IOException("Empty response from Microsoft")

        if (!response.isSuccessful) {
            LauncherLogger.error("Device code request failed with HTTP ${response.code}")
            throw IOException("Failed to get device code: $responseBody")
        }

        val json = JSONObject(responseBody)
        DeviceCodeResponse(
            deviceCode = json.getString("device_code"),
            userCode = json.getString("user_code"),
            verificationUri = json.optString("verification_uri", "https://microsoft.com/link"),
            expiresIn = json.optInt("expires_in", 900),
            interval = json.optInt("interval", 5),
            message = json.optString("message", "Please visit https://microsoft.com/link and enter code")
        )
    }

    suspend fun pollForToken(
        deviceCode: String,
        intervalSeconds: Int,
        expiresInSeconds: Int,
        onStatusUpdate: (String) -> Unit
    ): MicrosoftTokenResponse = withContext(Dispatchers.IO) {
        val startTime = System.currentTimeMillis()
        val maxDurationMs = expiresInSeconds * 1000L
        val intervalMs = (intervalSeconds.coerceAtLeast(3)) * 1000L

        LauncherLogger.info("Waiting for user to approve Microsoft sign-in on website...")
        while (System.currentTimeMillis() - startTime < maxDurationMs) {
            delay(intervalMs)

            val formBody = FormBody.Builder()
                .add("client_id", CLIENT_ID)
                .add("grant_type", "urn:ietf:params:oauth:grant-type:device_code")
                .add("device_code", deviceCode)
                .build()

            val request = Request.Builder()
                .url(TOKEN_URL)
                .post(formBody)
                .header("Accept", "application/json")
                .build()

            val response = okHttpClient.newCall(request).execute()
            val body = response.body?.string() ?: ""

            if (response.isSuccessful) {
                val json = JSONObject(body)
                LauncherLogger.info("Microsoft OAuth authorization approved!")
                return@withContext MicrosoftTokenResponse(
                    accessToken = json.getString("access_token"),
                    refreshToken = json.getString("refresh_token"),
                    expiresIn = json.optInt("expires_in", 3600)
                )
            } else {
                val errorJson = try { JSONObject(body) } catch (_: Exception) { null }
                val errorCode = errorJson?.optString("error") ?: ""

                when (errorCode) {
                    "authorization_pending" -> {
                        onStatusUpdate("Waiting for authorization on browser...")
                    }
                    "slow_down" -> {
                        delay(5000)
                    }
                    "expired_token" -> {
                        throw IOException("Device authorization code expired. Please try again.")
                    }
                    "access_denied" -> {
                        throw IOException("Sign-in request was denied by user.")
                    }
                    else -> {
                        throw IOException("OAuth token error: ${errorJson?.optString("error_description") ?: body}")
                    }
                }
            }
        }
        throw IOException("Authentication timed out. Please try again.")
    }

    suspend fun refreshMicrosoftToken(refreshToken: String): MicrosoftTokenResponse = withContext(Dispatchers.IO) {
        val formBody = FormBody.Builder()
            .add("client_id", CLIENT_ID)
            .add("grant_type", "refresh_token")
            .add("refresh_token", refreshToken)
            .add("scope", SCOPE)
            .build()

        val request = Request.Builder()
            .url(TOKEN_URL)
            .post(formBody)
            .header("Accept", "application/json")
            .build()

        LauncherLogger.info("Refreshing Microsoft access token...")
        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: throw IOException("Empty response during token refresh")

        if (!response.isSuccessful) {
            LauncherLogger.error("Failed to refresh Microsoft token: HTTP ${response.code}")
            throw IOException("Token refresh failed: $body")
        }

        val json = JSONObject(body)
        MicrosoftTokenResponse(
            accessToken = json.getString("access_token"),
            refreshToken = json.optString("refresh_token", refreshToken),
            expiresIn = json.optInt("expires_in", 3600)
        )
    }
}
