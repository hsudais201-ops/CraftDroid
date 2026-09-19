package com.example.skin

import android.content.ContentValues
import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import com.example.core.db.AccountDao
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File
import java.io.FileOutputStream
import java.io.IOException

class SkinManager(
    private val context: Context,
    private val okHttpClient: OkHttpClient,
    private val fileSystem: MinecraftFileSystem,
    private val accountDao: AccountDao
) {

    /**
     * Reads an image from an Android content Uri (e.g. from PhotoPicker), validates
     * or adapts it to a 64x64 Minecraft skin PNG, saves it to internal storage,
     * and associates it with the account in the database.
     */
    suspend fun saveCustomSkin(
        uuid: String,
        sourceUri: Uri,
        model: SkinModel = SkinModel.CLASSIC
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            LauncherLogger.info("Processing custom skin from URI: $sourceUri for account: $uuid")
            val inputStream = context.contentResolver.openInputStream(sourceUri)
                ?: return@withContext Result.failure(IOException("Failed to open skin image stream"))

            val originalBitmap = BitmapFactory.decodeStream(inputStream)
                ?: return@withContext Result.failure(IOException("Invalid image data: unable to decode skin"))

            val normalizedBitmap = normalizeSkinBitmap(originalBitmap)
            val skinFile = fileSystem.getSkinFile(uuid)

            FileOutputStream(skinFile).use { out ->
                normalizedBitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }

            // Update database entity
            val fileUriString = Uri.fromFile(skinFile).toString()
            val existing = accountDao.getAccountByUuid(uuid)
            if (existing != null) {
                accountDao.insertAccount(
                    existing.copy(
                        skinUrl = fileUriString,
                        skinModel = model.id
                    )
                )
            }

            LauncherLogger.info("Saved custom skin to ${skinFile.absolutePath} (model: ${model.label})")
            Result.success(skinFile)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to save custom skin: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Generates and applies a built-in preset skin (Steve, Alex, Cyberpunk, etc.)
     */
    suspend fun applyPresetSkin(
        uuid: String,
        preset: SkinPreset
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            LauncherLogger.info("Applying preset skin '${preset.name}' to account: $uuid")
            val bitmap = SkinTextureGenerator.generatePresetBitmap(preset)
            val skinFile = fileSystem.getSkinFile(uuid)

            FileOutputStream(skinFile).use { out ->
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }

            val fileUriString = Uri.fromFile(skinFile).toString()
            val existing = accountDao.getAccountByUuid(uuid)
            if (existing != null) {
                accountDao.insertAccount(
                    existing.copy(
                        skinUrl = fileUriString,
                        skinModel = preset.model.id,
                        avatarType = preset.id
                    )
                )
            }

            LauncherLogger.info("Preset skin '${preset.name}' applied successfully")
            Result.success(skinFile)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to apply preset skin: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Fetches a skin PNG from a direct URL and associates it with the account.
     */
    suspend fun fetchSkinFromUrl(
        uuid: String,
        url: String,
        model: SkinModel = SkinModel.CLASSIC
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            LauncherLogger.info("Fetching skin from URL: $url")
            val request = Request.Builder().url(url).build()
            val response = okHttpClient.newCall(request).execute()

            if (!response.isSuccessful) {
                return@withContext Result.failure(IOException("HTTP error ${response.code} downloading skin"))
            }

            val bytes = response.body?.bytes()
                ?: return@withContext Result.failure(IOException("Empty response body"))

            val originalBitmap = BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
                ?: return@withContext Result.failure(IOException("Decoded image is null or corrupted"))

            val normalizedBitmap = normalizeSkinBitmap(originalBitmap)
            val skinFile = fileSystem.getSkinFile(uuid)

            FileOutputStream(skinFile).use { out ->
                normalizedBitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
            }

            val fileUriString = Uri.fromFile(skinFile).toString()
            val existing = accountDao.getAccountByUuid(uuid)
            if (existing != null) {
                accountDao.insertAccount(
                    existing.copy(
                        skinUrl = fileUriString,
                        skinModel = model.id
                    )
                )
            }

            LauncherLogger.info("Skin fetched from URL saved to ${skinFile.absolutePath}")
            Result.success(skinFile)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to fetch skin from URL: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Fetches a skin using a player's Minecraft username.
     * Uses minotar.net/skin or mc-heads.net.
     */
    suspend fun fetchSkinByPlayerName(
        uuid: String,
        playerName: String,
        model: SkinModel = SkinModel.CLASSIC
    ): Result<File> = withContext(Dispatchers.IO) {
        val cleanName = playerName.trim()
        if (cleanName.isBlank()) {
            return@withContext Result.failure(IllegalArgumentException("Player name cannot be empty"))
        }

        val url = "https://minotar.net/skin/$cleanName"
        fetchSkinFromUrl(uuid, url, model)
    }

    /**
     * Uploads the active skin to official Mojang / Minecraft services
     * for authenticated Microsoft accounts.
     */
    suspend fun uploadSkinToMojang(
        mcAccessToken: String,
        skinFile: File,
        model: SkinModel
    ): Result<Boolean> = withContext(Dispatchers.IO) {
        try {
            LauncherLogger.info("Uploading skin to Minecraft Services (Mojang API)...")
            val mediaType = "image/png".toMediaType()
            val fileBody = skinFile.asRequestBody(mediaType)

            val requestBody = MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("variant", model.id) // "classic" or "slim"
                .addFormDataPart("file", skinFile.name, fileBody)
                .build()

            val request = Request.Builder()
                .url("https://api.minecraftservices.com/minecraft/profile/skins")
                .header("Authorization", "Bearer $mcAccessToken")
                .post(requestBody)
                .build()

            val response = okHttpClient.newCall(request).execute()
            if (response.isSuccessful || response.code == 204) {
                LauncherLogger.info("Skin successfully uploaded to Mojang servers!")
                Result.success(true)
            } else {
                val err = response.body?.string() ?: "HTTP ${response.code}"
                LauncherLogger.error("Mojang skin upload failed: $err")
                Result.failure(IOException("Mojang skin upload rejected: $err"))
            }
        } catch (e: Exception) {
            LauncherLogger.error("Exception during Mojang skin upload: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Exports the skin PNG to the device's public Pictures or Downloads directory.
     */
    suspend fun exportSkin(skinFile: File, username: String): Result<Uri> = withContext(Dispatchers.IO) {
        try {
            val fileName = "minecraft_skin_${username.filter { it.isLetterOrDigit() }}.png"
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val contentValues = ContentValues().apply {
                    put(MediaStore.MediaColumns.DISPLAY_NAME, fileName)
                    put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
                    put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/MinecraftSkins")
                }
                val uri = context.contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
                    ?: return@withContext Result.failure(IOException("Failed to create MediaStore entry"))

                context.contentResolver.openOutputStream(uri)?.use { out ->
                    skinFile.inputStream().copyTo(out)
                }
                LauncherLogger.info("Skin exported to MediaStore: $uri")
                Result.success(uri)
            } else {
                val targetDir = File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_PICTURES), "MinecraftSkins")
                targetDir.mkdirs()
                val targetFile = File(targetDir, fileName)
                skinFile.copyTo(targetFile, overwrite = true)
                Result.success(Uri.fromFile(targetFile))
            }
        } catch (e: Exception) {
            LauncherLogger.error("Failed to export skin: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Resets the account's skin to default (Steve/Alex).
     */
    suspend fun resetSkin(uuid: String, defaultModel: SkinModel = SkinModel.CLASSIC): Result<Unit> = withContext(Dispatchers.IO) {
        try {
            val skinFile = fileSystem.getSkinFile(uuid)
            if (skinFile.exists()) {
                skinFile.delete()
            }
            val existing = accountDao.getAccountByUuid(uuid)
            if (existing != null) {
                accountDao.insertAccount(
                    existing.copy(
                        skinUrl = null,
                        skinModel = defaultModel.id,
                        avatarType = "Default"
                    )
                )
            }
            LauncherLogger.info("Reset skin for account $uuid to default")
            Result.success(Unit)
        } catch (e: Exception) {
            LauncherLogger.error("Failed to reset skin: ${e.message}")
            Result.failure(e)
        }
    }

    /**
     * Ensures any provided bitmap conforms to canonical 64x64 Minecraft skin geometry.
     * Converts legacy 64x32 pre-1.8 skins to 64x64 modern standard by mirroring limbs.
     */
    private fun normalizeSkinBitmap(source: Bitmap): Bitmap {
        val w = source.width
        val h = source.height

        // Case 1: Standard modern 64x64
        if (w == 64 && h == 64) {
            return source
        }

        // Case 2: Legacy 64x32 (Pre-1.8 format). Convert to 64x64
        if (w == 64 && h == 32) {
            val output = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(output)
            val paint = Paint().apply { isAntiAlias = false }

            // Copy upper 32 rows as-is
            canvas.drawBitmap(source, 0f, 0f, paint)

            // Mirror Right Arm (44, 20, 12, 12) to Left Arm (36, 52)
            copyRect(source, canvas, paint, Rect(44, 20, 56, 32), Rect(36, 52, 48, 64))

            // Mirror Right Leg (4, 20, 16, 32) to Left Leg (20, 52)
            copyRect(source, canvas, paint, Rect(4, 20, 16, 32), Rect(20, 52, 32, 64))

            return output
        }

        // Case 3: Scaled / HD (e.g. 128x128). Scale down to 64x64
        if (w == h && w >= 64) {
            return Bitmap.createScaledBitmap(source, 64, 64, false)
        }

        // Fallback: Scale into 64x64 canvas
        val output = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(output)
        val paint = Paint().apply { isAntiAlias = false }
        val srcRect = Rect(0, 0, w, h)
        val dstRect = Rect(0, 0, 64, 64)
        canvas.drawBitmap(source, srcRect, dstRect, paint)
        return output
    }

    private fun copyRect(src: Bitmap, dstCanvas: Canvas, paint: Paint, srcRect: Rect, dstRect: Rect) {
        dstCanvas.drawBitmap(src, srcRect, dstRect, paint)
    }

    /**
     * Loads a Bitmap from a file URI or file path.
     */
    fun loadSkinBitmap(skinPathOrUrl: String?): Bitmap? {
        if (skinPathOrUrl == null) return null
        return try {
            if (skinPathOrUrl.startsWith("file://")) {
                val path = Uri.parse(skinPathOrUrl).path ?: return null
                BitmapFactory.decodeFile(path)
            } else if (skinPathOrUrl.startsWith("/")) {
                BitmapFactory.decodeFile(skinPathOrUrl)
            } else {
                null
            }
        } catch (e: Exception) {
            null
        }
    }
}
