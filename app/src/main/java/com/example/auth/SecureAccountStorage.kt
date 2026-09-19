package com.example.auth

import android.content.Context
import android.content.SharedPreferences
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import com.example.logs.LauncherLogger
import java.nio.ByteBuffer
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Keystore-backed AES/GCM credential storage with one-time legacy migration. */
class SecureAccountStorage(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("mc_secure_auth", Context.MODE_PRIVATE)

    companion object {
        private const val KEYSTORE = "AndroidKeyStore"
        private const val KEY_ALIAS = "CraftDroidAccountKey"
        private const val VERSION = "v2:"
        private const val IV_BYTES = 12
        private const val TAG_BITS = 128
        private val SECRET_PREFIXES = arrayOf("ms_refresh_", "mc_token_", "ely_refresh_", "ely_token_")
    }

    init {
        migrateLegacySecrets()
    }

    @Synchronized
    fun saveMicrosoftRefreshToken(uuid: String, refreshToken: String) {
        putSecret("ms_refresh_" + uuid, refreshToken)
    }

    fun getMicrosoftRefreshToken(uuid: String): String? = getSecret("ms_refresh_" + uuid)

    @Synchronized
    fun saveMinecraftAccessToken(uuid: String, token: String, expiresAt: Long) {
        putSecret("mc_token_" + uuid, token)
        prefs.edit().putLong("mc_token_exp_" + uuid, expiresAt).apply()
    }

    fun getMinecraftAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("mc_token_exp_" + uuid, 0L)
        if (expiresAt <= 0L || System.currentTimeMillis() >= expiresAt - 60_000L) return null
        return getSecret("mc_token_" + uuid)
    }

    fun getMinecraftAccessTokenExpiry(uuid: String): Long? =
        prefs.getLong("mc_token_exp_" + uuid, 0L).takeIf { it > 0L }

    @Synchronized
    fun saveElyByRefreshToken(uuid: String, refreshToken: String) {
        putSecret("ely_refresh_" + uuid, refreshToken)
    }

    fun getElyByRefreshToken(uuid: String): String? = getSecret("ely_refresh_" + uuid)

    @Synchronized
    fun saveElyByAccessToken(uuid: String, token: String, expiresAt: Long) {
        putSecret("ely_token_" + uuid, token)
        prefs.edit().putLong("ely_token_exp_" + uuid, expiresAt).apply()
    }

    fun getElyByAccessToken(uuid: String): String? {
        val expiresAt = prefs.getLong("ely_token_exp_" + uuid, 0L)
        if (expiresAt <= 0L || System.currentTimeMillis() >= expiresAt - 60_000L) return null
        return getSecret("ely_token_" + uuid)
    }

    @Synchronized
    fun clearTokens(uuid: String) {
        prefs.edit()
            .remove("ms_refresh_" + uuid)
            .remove("mc_token_" + uuid)
            .remove("mc_token_exp_" + uuid)
            .remove("ely_refresh_" + uuid)
            .remove("ely_token_" + uuid)
            .remove("ely_token_exp_" + uuid)
            .apply()
    }

    private fun putSecret(name: String, value: String) {
        require(value.isNotEmpty()) { "Credential value is empty" }
        prefs.edit().putString(name, VERSION + encrypt(value)).apply()
    }

    private fun getSecret(name: String): String? {
        val stored = prefs.getString(name, null) ?: return null
        if (!stored.startsWith(VERSION)) return null
        return try {
            decrypt(stored.removePrefix(VERSION))
        } catch (e: Throwable) {
            LauncherLogger.error("Credential decryption failed for " + name + ": " + e.message)
            null
        }
    }

    private fun migrateLegacySecrets() {
        val updates = mutableMapOf<String, String>()
        for ((name, raw) in prefs.all) {
            if (!SECRET_PREFIXES.any { name.startsWith(it) }) continue
            val value = raw as? String ?: continue
            if (value.isEmpty() || value.startsWith(VERSION)) continue
            try {
                updates[name] = VERSION + encrypt(value)
            } catch (e: Throwable) {
                LauncherLogger.error("Credential migration failed for " + name + ": " + e.message)
            }
        }
        if (updates.isNotEmpty()) {
            val editor = prefs.edit()
            updates.forEach { (name, value) -> editor.putString(name, value) }
            editor.apply()
        }
    }

    private fun key(): SecretKey {
        val store = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (store.getKey(KEY_ALIAS, null) as? SecretKey)?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build()
        )
        return generator.generateKey()
    }

    private fun encrypt(value: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val iv = cipher.iv
        require(iv.size == IV_BYTES) { "Unexpected AES-GCM IV size" }
        val ciphertext = cipher.doFinal(value.toByteArray(Charsets.UTF_8))
        return Base64.encodeToString(
            ByteBuffer.allocate(1 + iv.size + ciphertext.size)
                .put(iv.size.toByte())
                .put(iv)
                .put(ciphertext)
                .array(),
            Base64.NO_WRAP
        )
    }

    private fun decrypt(encoded: String): String {
        val data = Base64.decode(encoded, Base64.DEFAULT)
        require(data.size > 1 + IV_BYTES) { "Invalid encrypted credential envelope" }
        val ivLength = data[0].toInt() and 0xFF
        require(ivLength == IV_BYTES) { "Invalid encrypted credential IV size" }
        val iv = data.copyOfRange(1, 1 + ivLength)
        val ciphertext = data.copyOfRange(1 + ivLength, data.size)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, iv))
        return String(cipher.doFinal(ciphertext), Charsets.UTF_8)
    }
}
