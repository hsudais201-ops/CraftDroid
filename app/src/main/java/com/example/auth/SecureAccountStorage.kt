package com.example.auth

import android.content.Context
import android.content.SharedPreferences

/**
 * Manages encrypted / private key-value credentials for Microsoft and Minecraft tokens.
 * NEVER prints tokens in logs or exposes them to composables.
 */
class SecureAccountStorage(context: Context) {

    private val prefs: SharedPreferences = context.getSharedPreferences("mc_secure_auth", Context.MODE_PRIVATE)

    fun saveMicrosoftRefreshToken(uuid: String, refreshToken: String) {
        prefs.edit().putString("ms_refresh_$uuid", refreshToken).apply()
    }

    fun getMicrosoftRefreshToken(uuid: String): String? {
        return prefs.getString("ms_refresh_$uuid", null)
    }

    fun saveMinecraftAccessToken(uuid: String, token: String, expiresAt: Long) {
        prefs.edit()
            .putString("mc_token_$uuid", token)
            .putLong("mc_token_exp_$uuid", expiresAt)
            .apply()
    }

    fun getMinecraftAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("mc_token_exp_$uuid", 0)
        // If expired (or expiring within 60 seconds), return null to force refresh
        if (System.currentTimeMillis() >= expiresAt - 60000) {
            return null
        }
        return prefs.getString("mc_token_$uuid", null)
    }

    fun getMinecraftAccessTokenExpiry(uuid: String): Long? {
        val expiresAt = prefs.getLong("mc_token_exp_$uuid", 0)
        return expiresAt.takeIf { it > 0 }
    }

    fun saveElyByRefreshToken(uuid: String, refreshToken: String) {
        prefs.edit().putString("ely_refresh_$uuid", refreshToken).apply()
    }

    fun getElyByRefreshToken(uuid: String): String? {
        return prefs.getString("ely_refresh_$uuid", null)
    }

    fun saveElyByAccessToken(uuid: String, token: String, expiresAt: Long) {
        prefs.edit()
            .putString("ely_token_$uuid", token)
            .putLong("ely_token_exp_$uuid", expiresAt)
            .apply()
    }

    fun getElyByAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("ely_token_exp_$uuid", 0)
        if (System.currentTimeMillis() >= expiresAt - 60000) {
            return null
        }
        return prefs.getString("ely_token_$uuid", null)
    }

    fun clearTokens(uuid: String) {
        prefs.edit()
            .remove("ms_refresh_$uuid")
            .remove("mc_token_$uuid")
            .remove("mc_token_exp_$uuid")
            .remove("ely_refresh_$uuid")
            .remove("ely_token_$uuid")
            .remove("ely_token_exp_$uuid")
            .apply()
    }
}
