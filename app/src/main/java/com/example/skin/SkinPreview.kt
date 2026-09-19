package com.example.skin

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.InputStream
import java.net.URL

/**
 * Draws an authentic 2D front character model of a Minecraft skin.
 * Supports Classic (4px arms) and Slim (3px arms) with outer layers (Hat, Jacket, Sleeves, Pants).
 */
@Composable
fun MinecraftSkinCharacterView(
    skinBitmap: Bitmap?,
    model: SkinModel,
    modifier: Modifier = Modifier,
    scale: Float = 5.0f,
    showOuterLayers: Boolean = true
) {
    val displayBitmap = remember(skinBitmap) {
        skinBitmap ?: SkinTextureGenerator.generatePresetBitmap(SkinPresets.presets.first())
    }
    val imageBitmap = remember(displayBitmap) { displayBitmap.asImageBitmap() }

    // Total character width: 4 + 8 + 4 = 16 pixels (classic) or 3 + 8 + 3 = 14 pixels (slim)
    // Total character height: 8 (head) + 12 (torso) + 12 (legs) = 32 pixels
    val charWidthPx = if (model == SkinModel.CLASSIC) 16 else 14
    val charHeightPx = 32
    val armWidth = model.armWidth

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(Color(0xFF1E2328).copy(alpha = 0.9f))
            .border(1.dp, Color.White.copy(alpha = 0.15f), RoundedCornerShape(12.dp)),
        contentAlignment = Alignment.Center
    ) {
        Canvas(
            modifier = Modifier.size(
                width = (charWidthPx * scale).dp,
                height = (charHeightPx * scale).dp
            )
        ) {
            val pixel = size.height / charHeightPx.toFloat()

            // 1. Subtle drop shadow under feet
            drawOval(
                color = Color.Black.copy(alpha = 0.4f),
                topLeft = Offset(pixel, size.height - (1.5f * pixel)),
                size = Size(size.width - (2 * pixel), 3 * pixel)
            )

            val headX = (if (model == SkinModel.CLASSIC) 4 else 3) * pixel
            val torsoX = (if (model == SkinModel.CLASSIC) 4 else 3) * pixel
            val leftArmX = 0f
            val rightArmX = (if (model == SkinModel.CLASSIC) 12 else 11) * pixel
            val rightLegX = ((if (model == SkinModel.CLASSIC) 4 else 3)) * pixel
            val leftLegX = ((if (model == SkinModel.CLASSIC) 8 else 7)) * pixel

            // A. Head (Face 8x8 at src 8,8)
            drawSkinPart(imageBitmap, srcX = 8, srcY = 8, w = 8, h = 8, dstX = headX, dstY = 0f, pixel = pixel)
            if (showOuterLayers) {
                // Hat layer (8x8 at src 40,8)
                drawSkinPart(imageBitmap, srcX = 40, srcY = 8, w = 8, h = 8, dstX = headX, dstY = 0f, pixel = pixel)
            }

            // B. Torso (8x12 at src 20,20)
            val torsoY = 8 * pixel
            drawSkinPart(imageBitmap, srcX = 20, srcY = 20, w = 8, h = 12, dstX = torsoX, dstY = torsoY, pixel = pixel)
            if (showOuterLayers) {
                // Jacket layer (8x12 at src 20,36)
                drawSkinPart(imageBitmap, srcX = 20, srcY = 36, w = 8, h = 12, dstX = torsoX, dstY = torsoY, pixel = pixel)
            }

            // C. Right Arm (armWidth x 12 at src 44,20)
            drawSkinPart(imageBitmap, srcX = 44, srcY = 20, w = armWidth, h = 12, dstX = leftArmX, dstY = torsoY, pixel = pixel)
            if (showOuterLayers) {
                // Right Sleeve layer (src 44, 36)
                drawSkinPart(imageBitmap, srcX = 44, srcY = 36, w = armWidth, h = 12, dstX = leftArmX, dstY = torsoY, pixel = pixel)
            }

            // D. Left Arm (armWidth x 12 at src 36, 52)
            drawSkinPart(imageBitmap, srcX = 36, srcY = 52, w = armWidth, h = 12, dstX = rightArmX, dstY = torsoY, pixel = pixel)
            if (showOuterLayers) {
                // Left Sleeve layer (src 52, 52)
                drawSkinPart(imageBitmap, srcX = 52, srcY = 52, w = armWidth, h = 12, dstX = rightArmX, dstY = torsoY, pixel = pixel)
            }

            // E. Right Leg (4x12 at src 4, 20)
            val legsY = 20 * pixel
            drawSkinPart(imageBitmap, srcX = 4, srcY = 20, w = 4, h = 12, dstX = rightLegX, dstY = legsY, pixel = pixel)
            if (showOuterLayers) {
                // Right Pants layer (src 4, 36)
                drawSkinPart(imageBitmap, srcX = 4, srcY = 36, w = 4, h = 12, dstX = rightLegX, dstY = legsY, pixel = pixel)
            }

            // F. Left Leg (4x12 at src 20, 52)
            drawSkinPart(imageBitmap, srcX = 20, srcY = 52, w = 4, h = 12, dstX = leftLegX, dstY = legsY, pixel = pixel)
            if (showOuterLayers) {
                // Left Pants layer (src 4, 52)
                drawSkinPart(imageBitmap, srcX = 4, srcY = 52, w = 4, h = 12, dstX = leftLegX, dstY = legsY, pixel = pixel)
            }
        }
    }
}

private fun DrawScope.drawSkinPart(
    image: ImageBitmap,
    srcX: Int,
    srcY: Int,
    w: Int,
    h: Int,
    dstX: Float,
    dstY: Float,
    pixel: Float
) {
    drawImage(
        image = image,
        srcOffset = IntOffset(srcX, srcY),
        srcSize = IntSize(w, h),
        dstOffset = IntOffset(dstX.toInt(), dstY.toInt()),
        dstSize = IntSize((w * pixel).toInt(), (h * pixel).toInt()),
        filterQuality = FilterQuality.None
    )
}

@Composable
fun MinecraftSkinHeadView(
    skinUrl: String?,
    modifier: Modifier = Modifier,
    sizeDp: Int = 40
) {
    var loadedBitmap by remember(skinUrl) { mutableStateOf<Bitmap?>(null) }

    LaunchedEffect(skinUrl) {
        if (!skinUrl.isNullOrBlank()) {
            withContext(Dispatchers.IO) {
                try {
                    val file = java.io.File(skinUrl)
                    if (file.exists()) {
                        loadedBitmap = BitmapFactory.decodeFile(file.absolutePath)
                    } else if (skinUrl.startsWith("http://") || skinUrl.startsWith("https://")) {
                        val stream = URL(skinUrl).openStream()
                        loadedBitmap = BitmapFactory.decodeStream(stream)
                        stream.close()
                    }
                } catch (_: Exception) {
                    loadedBitmap = null
                }
            }
        }
    }

    MinecraftSkinHeadView(skinBitmap = loadedBitmap, modifier = modifier, sizeDp = sizeDp)
}

/**
 * Pixelated Minecraft 8x8 Face + Hat overlay Composable.
 * Perfect for avatars, chips, and lists.
 */
@Composable
fun MinecraftSkinHeadView(
    skinBitmap: Bitmap?,
    modifier: Modifier = Modifier,
    sizeDp: Int = 40
) {
    val displayBitmap = remember(skinBitmap) {
        skinBitmap ?: SkinTextureGenerator.generatePresetBitmap(SkinPresets.presets.first())
    }
    val imageBitmap = remember(displayBitmap) { displayBitmap.asImageBitmap() }

    Box(
        modifier = modifier
            .size(sizeDp.dp)
            .clip(RoundedCornerShape(6.dp))
            .background(Color(0xFF263238))
            .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(6.dp)),
        contentAlignment = Alignment.Center
    ) {
        Canvas(modifier = Modifier.size(sizeDp.dp)) {
            val pixel = size.width / 8f
            // Base face (8x8 from 8,8)
            drawImage(
                image = imageBitmap,
                srcOffset = IntOffset(8, 8),
                srcSize = IntSize(8, 8),
                dstOffset = IntOffset(0, 0),
                dstSize = IntSize(size.width.toInt(), size.height.toInt()),
                filterQuality = FilterQuality.None
            )
            // Hat overlay (8x8 from 40,8)
            drawImage(
                image = imageBitmap,
                srcOffset = IntOffset(40, 8),
                srcSize = IntSize(8, 8),
                dstOffset = IntOffset(0, 0),
                dstSize = IntSize(size.width.toInt(), size.height.toInt()),
                filterQuality = FilterQuality.None
            )
        }
    }
}
