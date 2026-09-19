package com.example.auth

import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

class MinecraftAuthManager(private val okHttpClient: OkHttpClient) {

    private val jsonMedia = "application/json; charset=utf-8".toMediaType()

    /**
     * Validates an already-issued Minecraft Services access token and makes sure it
     * still belongs to the account CraftDroid is about to launch.
     *
     * This is intentionally a lightweight session check: it does not re-run the
     * Microsoft -> Xbox -> XSTS exchange unless the cached token is missing/expired.
     */
    suspend fun validateSession(accessToken: String, expectedUuid: String): MinecraftAuthResult =
        withContext(Dispatchers.IO) {
            val (uuid, username, skinUrl) = getMinecraftProfile(accessToken)
            if (!uuid.equals(expectedUuid, ignoreCase = true)) {
                throw IOException(
                    "Minecraft session belongs to a different account (expected $expectedUuid, got $uuid)."
                )
            }
            MinecraftAuthResult(
                uuid = uuid,
                username = username,
                accessToken = accessToken,
                userHash = "",
                skinUrl = skinUrl,
                expiresIn = 0
            )
        }

    suspend fun authenticateWithMicrosoft(msAccessToken: String): MinecraftAuthResult = withContext(Dispatchers.IO) {
        LauncherLogger.info("Authenticating with Xbox Live...")
        val (xblToken, userHash) = authenticateXboxLive(msAccessToken)

        LauncherLogger.info("Authorizing with XSTS...")
        val xstsToken = authorizeXsts(xblToken)

        LauncherLogger.info("Logging in to Minecraft Services...")
        val (mcAccessToken, expiresIn) = loginWithXbox(userHash, xstsToken)

        LauncherLogger.info("Verifying Minecraft ownership...")
        checkOwnership(mcAccessToken)

        LauncherLogger.info("Retrieving Minecraft profile...")
        val (uuid, username, skinUrl) = getMinecraftProfile(mcAccessToken)

        LauncherLogger.info("Successfully authenticated Minecraft profile: $username ($uuid)")
        MinecraftAuthResult(
            uuid = uuid,
            username = username,
            accessToken = mcAccessToken,
            userHash = userHash,
            skinUrl = skinUrl,
            expiresIn = expiresIn
        )
    }

    private fun authenticateXboxLive(msAccessToken: String): Pair<String, String> {
        val payload = JSONObject().apply {
            put("Properties", JSONObject().apply {
                put("AuthMethod", "RPS")
                put("SiteName", "user.auth.xboxlive.com")
                put("RpsTicket", "d=$msAccessToken")
            })
            put("RelyingParty", "http://auth.xboxlive.com")
            put("TokenType", "JWT")
        }

        val request = Request.Builder()
            .url("https://user.auth.xboxlive.com/user/authenticate")
            .post(payload.toString().toRequestBody(jsonMedia))
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: throw IOException("Empty Xbox Live response")

        if (!response.isSuccessful) {
            LauncherLogger.error("Xbox Live auth failed: HTTP ${response.code}")
            throw IOException("Xbox Live authentication failed")
        }

        val json = JSONObject(body)
        val token = json.getString("Token")
        val uhs = json.getJSONObject("DisplayClaims")
            .getJSONArray("xui")
            .getJSONObject(0)
            .getString("uhs")
        return Pair(token, uhs)
    }

    private fun authorizeXsts(xblToken: String): String {
        val payload = JSONObject().apply {
            put("Properties", JSONObject().apply {
                put("SandboxId", "RETAIL")
                put("UserTokens", JSONArray().apply { put(xblToken) })
            })
            put("RelyingParty", "rp://api.minecraftservices.com/")
            put("TokenType", "JWT")
        }

        val request = Request.Builder()
            .url("https://xsts.auth.xboxlive.com/xsts/authorize")
            .post(payload.toString().toRequestBody(jsonMedia))
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: throw IOException("Empty XSTS response")

        if (!response.isSuccessful) {
            val errorJson = try { JSONObject(body) } catch (_: Exception) { null }
            val xErr = errorJson?.optLong("XErr", 0L) ?: 0L
            when (xErr) {
                2148916233L -> throw IOException("Account has no Xbox Live account. Please create one on xbox.com")
                2148916238L -> throw IOException("Child account detected. Account must be added to a Family by an adult")
                else -> throw IOException("XSTS authorization failed: HTTP ${response.code}")
            }
        }

        val json = JSONObject(body)
        return json.getString("Token")
    }

    private fun loginWithXbox(userHash: String, xstsToken: String): Pair<String, Int> {
        val payload = JSONObject().apply {
            put("identityToken", "XBL3.0 x=$userHash;$xstsToken")
        }

        val request = Request.Builder()
            .url("https://api.minecraftservices.com/authentication/login_with_xbox")
            .post(payload.toString().toRequestBody(jsonMedia))
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: throw IOException("Empty Minecraft Services response")

        if (!response.isSuccessful) {
            LauncherLogger.error("Minecraft Services login failed: HTTP ${response.code}")
            throw IOException("Minecraft Services login failed")
        }

        val json = JSONObject(body)
        val accessToken = json.getString("access_token")
        val expiresIn = json.optInt("expires_in", 86400)
        return Pair(accessToken, expiresIn)
    }

    private fun checkOwnership(mcAccessToken: String) {
        val request = Request.Builder()
            .url("https://api.minecraftservices.com/entitlements/mcstore")
            .get()
            .header("Authorization", "Bearer $mcAccessToken")
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: ""

        if (response.isSuccessful) {
            val json = JSONObject(body)
            val items = json.optJSONArray("items")
            val ownsGame = (0 until (items?.length() ?: 0)).any { i ->
                val name = items?.getJSONObject(i)?.optString("name") ?: ""
                name.contains("minecraft", ignoreCase = true)
            }
            if (!ownsGame) {
                LauncherLogger.warn("Note: Minecraft license not explicitly confirmed in store entitlements, proceeding with profile lookup.")
            }
        }
    }

    private fun getMinecraftProfile(mcAccessToken: String): Triple<String, String, String?> {
        val request = Request.Builder()
            .url("https://api.minecraftservices.com/minecraft/profile")
            .get()
            .header("Authorization", "Bearer $mcAccessToken")
            .header("Accept", "application/json")
            .build()

        val response = okHttpClient.newCall(request).execute()
        val body = response.body?.string() ?: throw IOException("Empty profile response")

        if (response.code == 404) {
            throw IOException("Minecraft profile not found. This account does not own Minecraft: Java Edition.")
        }

        if (!response.isSuccessful) {
            throw IOException("Failed to load Minecraft profile: HTTP ${response.code}")
        }

        val json = JSONObject(body)
        val uuid = json.getString("id")
        val username = json.getString("name")

        var skinUrl: String? = null
        val skins = json.optJSONArray("skins")
        if (skins != null && skins.length() > 0) {
            val skin = skins.getJSONObject(0)
            skinUrl = skin.optString("url")
        }

        return Triple(uuid, username, skinUrl)
    }
}
