#!/usr/bin/env python3
"""Full source-boundary hardening pass for the extracted CraftDroid Android app."""
from pathlib import Path
import re
import sys

MARKER = "// STEP_FULL_CODEBASE_SWEEP"

SECURE_STORAGE = r'''package com.example.auth

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
'''

BACKUP = '''<?xml version="1.0" encoding="utf-8"?>
<full-backup-content>
    <exclude domain="sharedpref" path="mc_secure_auth.xml" />
</full-backup-content>
'''
DATA_RULES = '''<?xml version="1.0" encoding="utf-8"?>
<data-extraction-rules>
    <cloud-backup>
        <exclude domain="sharedpref" path="mc_secure_auth.xml" />
    </cloud-backup>
    <device-transfer>
        <exclude domain="sharedpref" path="mc_secure_auth.xml" />
    </device-transfer>
</data-extraction-rules>
'''

def patch(root: Path, rel: str, fn):
    p = root / rel
    if not p.is_file():
        raise SystemExit(f"[full-sweep] missing {rel}")
    p.write_text(fn(p.read_text(encoding="utf-8")), encoding="utf-8")

def replace_file(root: Path, rel: str, content: str):
    p = root / rel
    if not p.is_file():
        raise SystemExit(f"[full-sweep] missing {rel}")
    p.write_text(content, encoding="utf-8")

def patch_secure(root):
    replace_file(root, "app/src/main/java/com/example/auth/SecureAccountStorage.kt", SECURE_STORAGE)

def patch_backups(root):
    replace_file(root, "app/src/main/res/xml/backup_rules.xml", BACKUP)
    replace_file(root, "app/src/main/res/xml/data_extraction_rules.xml", DATA_RULES)

def patch_installer(root):
    rel = "app/src/main/java/com/example/minecraft/MinecraftInstaller.kt"
    def f(s):
        if MARKER not in s:
            s = s.replace("class MinecraftInstaller(", MARKER + "\n\nclass MinecraftInstaller(", 1)
        s = s.replace(
            '''            if (!assetsSuccess) {
                LauncherLogger.warn("Some secondary assets failed to download, game may still launch.")
            }''',
            '''            if (!assetsSuccess) {
                throw IOException("One or more Minecraft asset downloads failed; installation is incomplete")
            }''',
            1,
        )
        original_index = '        } catch (e: Exception) {\n            LauncherLogger.error("Error reading asset index: ' + '$' + '{e.message}")\n        }\n        return tasks'
        s = s.replace(
            original_index,
            '        } catch (e: Exception) {\n            LauncherLogger.error("Error reading asset index: " + e.message)\n            throw IOException("Minecraft asset index could not be parsed", e)\n        }\n        return tasks',
            1,
        )
        original_native = '        } catch (e: Exception) {\n            LauncherLogger.warn("Error extracting natives from ' + '$' + '{jarFile.name}: ' + '$' + '{e.message}")\n        }'
        s = s.replace(
            original_native,
            '        } catch (e: Exception) {\n            LauncherLogger.error("Error extracting natives from " + jarFile.name + ": " + e.message)\n            throw e\n        }',
            1,
        )
        return s
    patch(root, rel, f)

def patch_downloads(root):
    rel = "app/src/main/java/com/example/downloader/DownloadManager.kt"
    def f(s):
        if MARKER not in s:
            s = s.replace(
                "class DownloadManager(private val okHttpClient: OkHttpClient) {",
                MARKER + '''
class DownloadManager(private val okHttpClient: OkHttpClient) {
    private val trustedHttpClient = okHttpClient.newBuilder()
        .followRedirects(false)
        .followSslRedirects(false)
        .build()
''',
                1,
            )
        if "private fun validateDownloadUrl" not in s:
            anchor = "    suspend fun downloadSingleFile("
            helper = '''    private fun validateDownloadUrl(rawUrl: String): java.net.URL {
        val url = java.net.URL(rawUrl)
        require(url.protocol.equals("https", true)) { "Only HTTPS downloads are allowed: " + rawUrl }
        require(url.userInfo == null) { "Credential-bearing download URL rejected" }
        return url
    }

    private fun executeTrusted(rawUrl: String): okhttp3.Response {
        var current = validateDownloadUrl(rawUrl)
        repeat(6) { attempt ->
            val response = trustedHttpClient.newCall(
                okhttp3.Request.Builder()
                    .url(current)
                    .header("User-Agent", "CraftDroid-Launcher/2.5")
                    .build()
            ).execute()
            if (!response.isRedirect) return response
            val location = response.header("Location")
            response.close()
            if (location.isNullOrBlank()) throw IOException("Redirect has no Location header")
            if (attempt == 5) throw IOException("Too many redirects")
            current = current.toURI().resolve(location).toURL()
            validateDownloadUrl(current.toString())
        }
        throw IOException("Download redirect chain failed")
    }

'''
            s = s.replace(anchor, helper + anchor, 1)
        s = re.sub(
            r'''val request = Request\.Builder\(\)\s*\.url\(task\.url\)\s*\.header\("User-Agent", "CraftDroid-Launcher/1\.3"\)\s*\.build\(\)\s*\n\s*okHttpClient\.newCall\(request\)\.execute\(\)\.use \{ response ->''',
            '''executeTrusted(task.url).use { response ->''',
            s,
            count=2,
        )
        s = s.replace(
            '''                if (verifyHash && !task.expectedSha1.isNullOrBlank()) {
                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {''',
            '''                if (task.size > 0L && tempFile.length() != task.size) {
                    tempFile.delete()
                    throw IOException("Size mismatch for " + task.name + ": " + tempFile.length() + " != " + task.size)
                }
                if (verifyHash && !task.expectedSha1.isNullOrBlank()) {
                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {''',
            1,
        )
        s = s.replace(
            '''                                if (!task.expectedSha1.isNullOrBlank()) {
                                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {''',
            '''                                if (task.size > 0L && tempFile.length() != task.size) {
                                    tempFile.delete()
                                    throw IOException("Size mismatch for " + task.name + ": " + tempFile.length() + " != " + task.size)
                                }
                                if (!task.expectedSha1.isNullOrBlank()) {
                                    if (!HashVerifier.verifySha1(tempFile, task.expectedSha1)) {''',
            1,
        )
        return s
    patch(root, rel, f)

def patch_filesystem(root):
    rel = "app/src/main/java/com/example/filesystem/MinecraftFileSystem.kt"
    def f(s):
        s = s.replace(
            "    fun getAssetObjectFile(hash: String): File {\n",
            '    fun getAssetObjectFile(hash: String): File {\n        require(hash.matches(Regex("^[a-fA-F0-9]{40}$"))) { "Invalid asset hash" }\n',
            1,
        )
        s = s.replace(
            "        } catch (_: Exception) {}",
            '        } catch (e: Exception) {\n            com.example.logs.LauncherLogger.warn("Could not clean native temp directory: " + e.message)\n        }',
            1,
        )
        return s
    patch(root, rel, f)

def patch_version_managers(root):
    patch(root, "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt", lambda s: s.replace(
        '''        } catch (_: Throwable) {
            State.NOT_INSTALLED
        }''',
        '''        } catch (e: Throwable) {
            com.example.logs.LauncherLogger.warn("Could not read Minecraft install state for " + safeVersion + ": " + e.message)
            State.NOT_INSTALLED
        }''',
        1,
    ).replace(
        '''        } catch (_: Throwable) {
            false
        }
    }

    private fun libraryAllowed''',
        '''        } catch (e: Throwable) {
            com.example.logs.LauncherLogger.warn("Minecraft launch-readiness check failed for " + version + ": " + e.message)
            false
        }
    }

    private fun libraryAllowed''',
        1,
    ))
    def latest(s):
        if "import com.example.logs.LauncherLogger" not in s:
            s = s.replace("import org.json.JSONObject\n", "import org.json.JSONObject\nimport com.example.logs.LauncherLogger\n", 1)
        return s.replace(
            '''            val latest = try { fetch() } catch (_: Throwable) { null }''',
            '''            val latest = try { fetch() } catch (e: Throwable) {
                LauncherLogger.warn("Minecraft latest-version refresh failed: " + e.message)
                null
            }''',
            1,
        )
    patch(root, "app/src/main/java/com/example/launcher/MinecraftLatestVersionManager.kt", latest)
    patch(root, "app/src/main/java/com/example/launcher/DroidLauncherUpdateManager.kt", lambda s: s.replace(
        '''            val result = try { fetchLatest() } catch (_: Throwable) { null }''',
        '''            val result = try { fetchLatest() } catch (e: Throwable) {
                com.example.logs.LauncherLogger.warn("Launcher update check failed: " + e.message)
                null
            }''',
        1,
    ))

def patch_input_and_logs(root):
    def layout(s):
        if "import com.example.logs.LauncherLogger" not in s:
            s = s.replace("import org.json.JSONObject\n", "import org.json.JSONObject\nimport com.example.logs.LauncherLogger\n", 1)
        return s.replace(
            '''                try {
                    list.add(TouchControl.fromJson(item))
                } catch (_: Exception) {}''',
            '''                try {
                    list.add(TouchControl.fromJson(item))
                } catch (e: Exception) {
                    LauncherLogger.warn("Ignoring malformed touch control at index " + i + ": " + e.message)
                }''',
            1,
        )
    patch(root, "app/src/main/java/com/example/input/ControlLayout.kt", layout)
    patch(root, "app/src/main/java/com/example/logs/MinecraftProcessMonitor.kt", lambda s: s.replace(
        '''        }.getOrDefault("")

        if (tail.isNotEmpty()) {''',
        '''        }.onFailure { LauncherLogger.warn("Could not compact Minecraft event log: " + it.message) }
            .getOrDefault("")

        if (tail.isNotEmpty())''',
        1,
    ))

def patch_manifest(root):
    patch(root, "app/src/main/AndroidManifest.xml", lambda s: s.replace('        android:largeHeap="true"\n', '', 1))

def validate(root):
    checks = {
        "app/src/main/java/com/example/auth/SecureAccountStorage.kt": ("AndroidKeyStore", "AES/GCM/NoPadding", "CraftDroidAccountKey"),
        "app/src/main/res/xml/backup_rules.xml": ("mc_secure_auth.xml",),
        "app/src/main/res/xml/data_extraction_rules.xml": ("mc_secure_auth.xml",),
        "app/src/main/java/com/example/minecraft/MinecraftInstaller.kt": ("installation is incomplete", "asset index could not be parsed"),
        "app/src/main/java/com/example/downloader/HashVerifier.kt": ("file.length() <= 0L",),
        "app/src/main/java/com/example/downloader/DownloadManager.kt": ("executeTrusted", "Only HTTPS downloads are allowed", "followRedirects(false)", "sizeValid"),
        "app/src/main/java/com/example/filesystem/MinecraftFileSystem.kt": ("Invalid asset hash",),
        "app/src/main/java/com/example/input/ControlLayout.kt": ("Ignoring malformed touch control",),
    }
    for rel, needles in checks.items():
        text = (root / rel).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise SystemExit(f"[full-sweep] {rel} missing {needle}")
    for rel in ("app/src/main/res/xml/backup_rules.xml", "app/src/main/res/xml/data_extraction_rules.xml"):
        if "TODO" in (root / rel).read_text(encoding="utf-8"):
            raise SystemExit(f"[full-sweep] unfinished backup-rule TODO remains in {rel}")
    for p in (root / "app/src/main/java").rglob("*.kt"):
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\b(?:TODO|FIXME|NotImplementedException)\b", text):
            raise SystemExit(f"[full-sweep] unfinished marker remains in live source: {p}")

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    if not (root / "settings.gradle.kts").is_file():
        raise SystemExit(f"[full-sweep] Gradle root not found: {root}")
    patch_secure(root)
    patch_backups(root)
    patch_installer(root)
    patch_downloads(root)
    patch_filesystem(root)
    patch_version_managers(root)
    patch_input_and_logs(root)
    patch_manifest(root)
    validate(root)
    print("[full-sweep] PASS: source security, error handling, install atomicity and low-RAM cleanup repairs applied")

if __name__ == "__main__":
    main()
