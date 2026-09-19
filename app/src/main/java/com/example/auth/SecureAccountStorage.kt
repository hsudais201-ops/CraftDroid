package com.example.auth

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import com.example.logs.LauncherLogger
import java.nio.charset.StandardCharsets
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties

/**
 * Stores authentication credentials encrypted with an Android Keystore AES-GCM key.
 * Legacy plaintext values are migrated on first read and removed from SharedPreferences.
 */
class SecureAccountStorage(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val keyAlias = "$PREFS_NAME.key"

    private companion object {
        const val PREFS_NAME = "mc_secure_auth"
        const val TRANSFORM = "AES/GCM/NoPadding"
        const val KEYSTORE = "AndroidKeyStore"
        const val VERSION = 1
        const val TAG_BITS = 128
    }

    init {
        ensureKey()
        migrateLegacyPlaintext()
    }

    fun saveMicrosoftRefreshToken(uuid: String, refreshToken: String) { save("ms_refresh_$uuid", refreshToken) }
    fun getMicrosoftRefreshToken(uuid: String): String? = get("ms_refresh_$uuid")

    fun saveMinecraftAccessToken(uuid: String, token: String, expiresAt: Long) {
        save("mc_token_$uuid", token)
        prefs.edit().putLong("mc_token_exp_$uuid", expiresAt).apply()
    }

    fun getMinecraftAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("mc_token_exp_$uuid", 0L)
        if (expiresAt <= 0L || System.currentTimeMillis() >= expiresAt - 60_000L) return null
        return get("mc_token_$uuid")
    }

    fun getMinecraftAccessTokenExpiry(uuid: String): Long? =
        prefs.getLong("mc_token_exp_$uuid", 0L).takeIf { it > 0L }

    fun saveElyByRefreshToken(uuid: String, refreshToken: String) { save("ely_refresh_$uuid", refreshToken) }
    fun getElyByRefreshToken(uuid: String): String? = get("ely_refresh_$uuid")

    fun saveElyByAccessToken(uuid: String, token: String, expiresAt: Long) {
        save("ely_token_$uuid", token)
        prefs.edit().putLong("ely_token_exp_$uuid", expiresAt).apply()
    }

    fun getElyByAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("ely_token_exp_$uuid", 0L)
        if (expiresAt <= 0L || System.currentTimeMillis() >= expiresAt - 60_000L) return null
        return get("ely_token_$uuid")
    }

    fun clearTokens(uuid: String) {
        prefs.edit()
            .remove("ms_refresh_$uuid").remove("mc_token_$uuid").remove("mc_token_exp_$uuid")
            .remove("ely_refresh_$uuid").remove("ely_token_$uuid").remove("ely_token_exp_$uuid").apply()
    }

    private fun save(key: String, value: String) {
        val encrypted = encrypt(value.toByteArray(StandardCharsets.UTF_8))
        prefs.edit().putString("$key.cipher", encrypted).remove(key).apply()
    }

    private fun get(key: String): String? {
        val encrypted = prefs.getString("$key.cipher", null)
        if (!encrypted.isNullOrBlank()) {
            return try {
                decrypt(encrypted).toString(StandardCharsets.UTF_8)
            } catch (e: Exception) {
                LauncherLogger.error("Encrypted credential read failed for " + key + "; clearing the unreadable value.")
                prefs.edit().remove("$key.cipher").apply()
                null
            }
        }
        val legacy = prefs.getString(key, null)
        if (!legacy.isNullOrBlank()) {
            save(key, legacy)
            LauncherLogger.info("Migrated legacy plaintext credential " + key + " into Android Keystore storage.")
            return legacy
        }
        return null
    }

    private fun migrateLegacyPlaintext() {
        val protectedKeys = prefs.all.keys.filter {
            (it.startsWith("ms_refresh_") || it.startsWith("mc_token_") || it.startsWith("ely_refresh_") || it.startsWith("ely_token_")) && !it.endsWith(".cipher")
        }
        for (key in protectedKeys) {
            val value = prefs.getString(key, null) ?: continue
            runCatching { save(key, value) }.onFailure { error ->
                LauncherLogger.error("Credential migration failed for " + key + ": " + error.message)
            }
        }
    }

    private fun ensureKey(): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (ks.getKey(keyAlias, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(keyAlias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setKeySize(256).setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build()
        )
        return generator.generateKey()
    }

    private fun key(): SecretKey = ensureKey()

    private fun encrypt(bytes: ByteArray): String {
        val cipher = Cipher.getInstance(TRANSFORM)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        val ciphertext = cipher.doFinal(bytes)
        val packed = ByteArray(1 + iv.size + ciphertext.size)
        packed[0] = VERSION.toByte()
        System.arraycopy(iv, 0, packed, 1, iv.size)
        System.arraycopy(ciphertext, 0, packed, 1 + iv.size, ciphertext.size)
        return Base64.encodeToString(packed, Base64.NO_WRAP)
    }

    private fun decrypt(encoded: String): ByteArray {
        val packed = Base64.decode(encoded, Base64.NO_WRAP)
        require(packed.isNotEmpty() && packed[0].toInt() == VERSION) { "Unsupported credential encryption version" }
        val ivLength = 12
        require(packed.size > 1 + ivLength) { "Encrypted credential payload is too small" }
        val iv = packed.copyOfRange(1, 1 + ivLength)
        val ciphertext = packed.copyOfRange(1 + ivLength, packed.size)
        val cipher = Cipher.getInstance(TRANSFORM)
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv))
        return cipher.doFinal(ciphertext)
    }
}
