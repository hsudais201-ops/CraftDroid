package com.example.skin

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect

object SkinTextureGenerator {

    /**
     * Generates a genuine 64x64 Minecraft Java Edition skin bitmap for a preset.
     */
    fun generatePresetBitmap(preset: SkinPreset): Bitmap {
        val bitmap = Bitmap.createBitmap(64, 64, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val paint = Paint().apply { isAntiAlias = false }

        // Fill background transparent
        bitmap.eraseColor(Color.TRANSPARENT)

        when (preset.id) {
            "steve" -> drawSteve(canvas, paint)
            "alex" -> drawAlex(canvas, paint)
            "cyber_steve" -> drawCyberSteve(canvas, paint)
            "diamond_knight" -> drawDiamondKnight(canvas, paint)
            "creeper_hoodie" -> drawCreeperHoodie(canvas, paint)
            "ender_sorcerer" -> drawEnderSorcerer(canvas, paint)
            "netherite_pioneer" -> drawNetheritePioneer(canvas, paint)
            "redstone_engineer" -> drawRedstoneEngineer(canvas, paint)
            "tuxedo_agent" -> drawTuxedoAgent(canvas, paint)
            "arctic_explorer" -> drawArcticExplorer(canvas, paint)
            else -> drawSteve(canvas, paint)
        }

        return bitmap
    }

    private fun fillRect(canvas: Canvas, paint: Paint, x: Int, y: Int, w: Int, h: Int, color: Int) {
        paint.color = color
        canvas.drawRect(Rect(x, y, x + w, y + h), paint)
    }

    private fun drawSteve(canvas: Canvas, paint: Paint) {
        val skinTone = Color.rgb(197, 142, 107)
        val hairColor = Color.rgb(74, 44, 23)
        val eyeWhite = Color.rgb(255, 255, 255)
        val eyeBlue = Color.rgb(44, 52, 150)
        val mouthColor = Color.rgb(112, 60, 36)
        val shirtCyan = Color.rgb(0, 172, 193)
        val pantsBlue = Color.rgb(43, 62, 142)
        val shoesGrey = Color.rgb(90, 90, 90)

        // Head (8x8)
        fillRect(canvas, paint, 8, 8, 8, 8, skinTone) // Face
        fillRect(canvas, paint, 8, 8, 8, 2, hairColor) // Fringe
        fillRect(canvas, paint, 8, 0, 8, 8, hairColor) // Top head
        fillRect(canvas, paint, 16, 0, 8, 8, skinTone) // Bottom head
        fillRect(canvas, paint, 0, 8, 8, 8, hairColor) // Right head
        fillRect(canvas, paint, 16, 8, 8, 8, hairColor) // Left head
        fillRect(canvas, paint, 24, 8, 8, 8, hairColor) // Back head

        // Eyes (Steve's classic pixel eyes at row 12)
        fillRect(canvas, paint, 9, 12, 2, 1, eyeWhite)
        fillRect(canvas, paint, 13, 12, 2, 1, eyeWhite)
        fillRect(canvas, paint, 10, 12, 1, 1, eyeBlue)
        fillRect(canvas, paint, 13, 12, 1, 1, eyeBlue)

        // Nose & Mouth / Beard
        fillRect(canvas, paint, 11, 13, 2, 1, Color.rgb(175, 120, 85))
        fillRect(canvas, paint, 11, 14, 2, 1, mouthColor)

        // Torso: Cyan Shirt
        fillRect(canvas, paint, 20, 20, 8, 12, shirtCyan)
        fillRect(canvas, paint, 20, 16, 8, 4, shirtCyan) // Top shoulders
        fillRect(canvas, paint, 28, 16, 8, 4, shirtCyan) // Bottom waist
        fillRect(canvas, paint, 32, 20, 8, 12, shirtCyan) // Back torso
        // Collar V-neck
        fillRect(canvas, paint, 23, 20, 2, 2, skinTone)

        // Right Arm (Cyan sleeve + skin)
        fillRect(canvas, paint, 44, 20, 4, 4, shirtCyan)
        fillRect(canvas, paint, 44, 24, 4, 8, skinTone)
        fillRect(canvas, paint, 44, 16, 4, 4, shirtCyan)

        // Left Arm (Cyan sleeve + skin)
        fillRect(canvas, paint, 36, 52, 4, 4, shirtCyan)
        fillRect(canvas, paint, 36, 56, 4, 8, skinTone)
        fillRect(canvas, paint, 36, 48, 4, 4, shirtCyan)

        // Right Leg (Pants + Shoes)
        fillRect(canvas, paint, 4, 20, 4, 10, pantsBlue)
        fillRect(canvas, paint, 4, 30, 4, 2, shoesGrey)
        fillRect(canvas, paint, 4, 16, 4, 4, pantsBlue)

        // Left Leg (Pants + Shoes)
        fillRect(canvas, paint, 20, 52, 4, 10, pantsBlue)
        fillRect(canvas, paint, 20, 62, 4, 2, shoesGrey)
        fillRect(canvas, paint, 20, 48, 4, 4, pantsBlue)
    }

    private fun drawAlex(canvas: Canvas, paint: Paint) {
        val skinTone = Color.rgb(228, 185, 150)
        val gingerHair = Color.rgb(180, 85, 30)
        val greenTunic = Color.rgb(92, 124, 60)
        val brownPants = Color.rgb(75, 55, 40)
        val darkBoots = Color.rgb(45, 40, 35)

        // Head
        fillRect(canvas, paint, 8, 8, 8, 8, skinTone)
        fillRect(canvas, paint, 8, 0, 8, 8, gingerHair) // Top
        fillRect(canvas, paint, 8, 8, 8, 3, gingerHair) // Front bangs
        fillRect(canvas, paint, 0, 8, 8, 8, gingerHair) // Right
        fillRect(canvas, paint, 16, 8, 8, 8, gingerHair) // Left
        fillRect(canvas, paint, 24, 8, 8, 8, gingerHair) // Back

        // Eyes (Green)
        fillRect(canvas, paint, 9, 12, 2, 1, Color.WHITE)
        fillRect(canvas, paint, 13, 12, 2, 1, Color.WHITE)
        fillRect(canvas, paint, 10, 12, 1, 1, Color.rgb(45, 140, 75))
        fillRect(canvas, paint, 13, 12, 1, 1, Color.rgb(45, 140, 75))

        // Torso: Green Tunic with Belt
        fillRect(canvas, paint, 20, 20, 8, 12, greenTunic)
        fillRect(canvas, paint, 20, 16, 8, 4, greenTunic)
        fillRect(canvas, paint, 32, 20, 8, 12, greenTunic)
        // Brown leather belt
        fillRect(canvas, paint, 20, 29, 8, 2, brownPants)
        fillRect(canvas, paint, 23, 29, 2, 2, Color.rgb(190, 160, 80)) // Gold buckle

        // Arms (Alex is slim 3-pixel)
        fillRect(canvas, paint, 44, 20, 3, 5, greenTunic)
        fillRect(canvas, paint, 44, 25, 3, 7, skinTone)
        fillRect(canvas, paint, 44, 16, 3, 4, greenTunic)

        fillRect(canvas, paint, 36, 52, 3, 5, greenTunic)
        fillRect(canvas, paint, 36, 57, 3, 7, skinTone)
        fillRect(canvas, paint, 36, 48, 3, 4, greenTunic)

        // Legs
        fillRect(canvas, paint, 4, 20, 4, 9, brownPants)
        fillRect(canvas, paint, 4, 29, 4, 3, darkBoots)
        fillRect(canvas, paint, 4, 16, 4, 4, brownPants)

        fillRect(canvas, paint, 20, 52, 4, 9, brownPants)
        fillRect(canvas, paint, 20, 61, 4, 3, darkBoots)
        fillRect(canvas, paint, 20, 48, 4, 4, brownPants)
    }

    private fun drawCyberSteve(canvas: Canvas, paint: Paint) {
        val carbonDark = Color.rgb(33, 33, 33)
        val neonCyan = Color.rgb(0, 229, 255)
        val skinTone = Color.rgb(180, 140, 110)
        val cyberSilver = Color.rgb(158, 158, 158)

        drawSteve(canvas, paint)

        // Cyan Cyber Visor on Hat Layer
        fillRect(canvas, paint, 40, 11, 8, 3, neonCyan)
        fillRect(canvas, paint, 32, 11, 8, 3, Color.rgb(0, 150, 180)) // Visor side
        fillRect(canvas, paint, 48, 11, 8, 3, Color.rgb(0, 150, 180)) // Visor side

        // Tech chestplate & glowing lines on Torso
        fillRect(canvas, paint, 20, 22, 8, 8, carbonDark)
        fillRect(canvas, paint, 21, 24, 6, 1, neonCyan)
        fillRect(canvas, paint, 23, 26, 2, 3, neonCyan)

        // Cybernetic right arm
        fillRect(canvas, paint, 44, 20, 4, 12, cyberSilver)
        fillRect(canvas, paint, 45, 23, 2, 1, neonCyan)
        fillRect(canvas, paint, 45, 28, 2, 1, neonCyan)
    }

    private fun drawDiamondKnight(canvas: Canvas, paint: Paint) {
        val diamondBlue = Color.rgb(77, 208, 225)
        val diamondDark = Color.rgb(0, 151, 167)
        val steelGrey = Color.rgb(97, 97, 97)
        val lapisBlue = Color.rgb(13, 71, 161)

        drawSteve(canvas, paint)

        // Diamond Helmet (Front + Hat layer)
        fillRect(canvas, paint, 40, 8, 8, 5, diamondBlue)
        fillRect(canvas, paint, 40, 13, 2, 3, diamondDark)
        fillRect(canvas, paint, 46, 13, 2, 3, diamondDark)
        fillRect(canvas, paint, 40, 0, 8, 8, diamondBlue) // Top

        // Diamond Chestplate
        fillRect(canvas, paint, 20, 20, 8, 12, diamondBlue)
        fillRect(canvas, paint, 22, 23, 4, 6, lapisBlue) // Lapis chest crest
        fillRect(canvas, paint, 20, 16, 8, 4, steelGrey) // Shoulders

        // Arm Armor
        fillRect(canvas, paint, 44, 20, 4, 10, diamondDark)
        fillRect(canvas, paint, 36, 52, 4, 10, diamondDark)

        // Leg Armor
        fillRect(canvas, paint, 4, 20, 4, 12, steelGrey)
        fillRect(canvas, paint, 4, 22, 4, 6, diamondBlue)
        fillRect(canvas, paint, 20, 52, 4, 12, steelGrey)
        fillRect(canvas, paint, 20, 54, 4, 6, diamondBlue)
    }

    private fun drawCreeperHoodie(canvas: Canvas, paint: Paint) {
        val creeperGreen = Color.rgb(76, 175, 80)
        val creeperDark = Color.rgb(27, 94, 32)
        val denimBlue = Color.rgb(38, 50, 56)

        drawSteve(canvas, paint)

        // Green Hoodie on Head (Outer layer)
        fillRect(canvas, paint, 40, 8, 8, 8, creeperGreen)
        fillRect(canvas, paint, 42, 10, 4, 4, Color.TRANSPARENT) // Face cutout

        // Green Torso with Creeper Face Emblem
        fillRect(canvas, paint, 20, 20, 8, 12, creeperGreen)
        // Creeper Face
        fillRect(canvas, paint, 22, 23, 1, 2, creeperDark) // Left eye
        fillRect(canvas, paint, 25, 23, 1, 2, creeperDark) // Right eye
        fillRect(canvas, paint, 23, 25, 2, 2, creeperDark) // Center mouth
        fillRect(canvas, paint, 22, 26, 1, 3, creeperDark) // Left mouth
        fillRect(canvas, paint, 25, 26, 1, 3, creeperDark) // Right mouth

        // Sleeves
        fillRect(canvas, paint, 44, 20, 4, 8, creeperGreen)
        fillRect(canvas, paint, 36, 52, 4, 8, creeperGreen)

        // Dark Denim Pants
        fillRect(canvas, paint, 4, 20, 4, 12, denimBlue)
        fillRect(canvas, paint, 20, 52, 4, 12, denimBlue)
    }

    private fun drawEnderSorcerer(canvas: Canvas, paint: Paint) {
        val obsidianDark = Color.rgb(26, 18, 36)
        val enderPurple = Color.rgb(156, 39, 176)
        val eyePink = Color.rgb(234, 128, 252)

        drawAlex(canvas, paint)

        // Dark hooded cowl
        fillRect(canvas, paint, 40, 8, 8, 8, obsidianDark)
        fillRect(canvas, paint, 40, 0, 8, 8, obsidianDark)
        // Glowing purple eyes in shadow
        fillRect(canvas, paint, 8, 8, 8, 8, Color.rgb(15, 10, 20))
        fillRect(canvas, paint, 9, 12, 2, 1, eyePink)
        fillRect(canvas, paint, 13, 12, 2, 1, eyePink)

        // Ender Robe
        fillRect(canvas, paint, 20, 20, 8, 12, obsidianDark)
        fillRect(canvas, paint, 23, 20, 2, 12, enderPurple) // Rune center strip
        fillRect(canvas, paint, 44, 20, 3, 12, obsidianDark)
        fillRect(canvas, paint, 36, 52, 3, 12, obsidianDark)
        fillRect(canvas, paint, 4, 20, 4, 12, obsidianDark)
        fillRect(canvas, paint, 20, 52, 4, 12, obsidianDark)
    }

    private fun drawNetheritePioneer(canvas: Canvas, paint: Paint) {
        val netherite = Color.rgb(55, 71, 79)
        val netheriteDark = Color.rgb(38, 50, 56)
        val goldAccent = Color.rgb(255, 179, 0)
        val lavaGlow = Color.rgb(255, 112, 67)

        drawSteve(canvas, paint)

        // Heavy Netherite Helm
        fillRect(canvas, paint, 40, 8, 8, 8, netherite)
        fillRect(canvas, paint, 42, 11, 4, 2, lavaGlow) // Glowing visor slit

        // Netherite Plated Torso
        fillRect(canvas, paint, 20, 20, 8, 12, netherite)
        fillRect(canvas, paint, 21, 28, 6, 2, goldAccent) // Gold belt
        fillRect(canvas, paint, 20, 16, 8, 4, netheriteDark)

        // Arms
        fillRect(canvas, paint, 44, 20, 4, 12, netheriteDark)
        fillRect(canvas, paint, 36, 52, 4, 12, netheriteDark)

        // Plated Legs
        fillRect(canvas, paint, 4, 20, 4, 12, netherite)
        fillRect(canvas, paint, 20, 52, 4, 12, netherite)
    }

    private fun drawRedstoneEngineer(canvas: Canvas, paint: Paint) {
        val brownLeather = Color.rgb(121, 85, 72)
        val redstoneRed = Color.rgb(229, 57, 53)
        val brassGold = Color.rgb(212, 175, 55)

        drawAlex(canvas, paint)

        // Brass Goggles on Hat Layer
        fillRect(canvas, paint, 40, 10, 8, 2, brassGold)
        fillRect(canvas, paint, 41, 10, 2, 2, redstoneRed) // Glowing lens
        fillRect(canvas, paint, 45, 10, 2, 2, brassGold)

        // Work Apron & Toolbelt
        fillRect(canvas, paint, 20, 20, 8, 12, brownLeather)
        fillRect(canvas, paint, 22, 22, 4, 6, redstoneRed) // Redstone battery
        fillRect(canvas, paint, 20, 29, 8, 2, Color.rgb(62, 39, 35)) // Dark belt
        fillRect(canvas, paint, 21, 29, 1, 2, brassGold) // Tool buckle
        fillRect(canvas, paint, 26, 29, 1, 2, redstoneRed) // Redstone pouch
    }

    private fun drawTuxedoAgent(canvas: Canvas, paint: Paint) {
        val tuxBlack = Color.rgb(28, 28, 28)
        val whiteShirt = Color.rgb(245, 245, 245)
        val redBowTie = Color.rgb(211, 47, 47)

        drawSteve(canvas, paint)

        // Clean hair
        fillRect(canvas, paint, 8, 0, 8, 8, tuxBlack)
        fillRect(canvas, paint, 0, 8, 8, 8, tuxBlack)
        fillRect(canvas, paint, 16, 8, 8, 8, tuxBlack)
        fillRect(canvas, paint, 24, 8, 8, 8, tuxBlack)

        // Tuxedo Jacket
        fillRect(canvas, paint, 20, 20, 8, 12, tuxBlack)
        // White shirt V
        fillRect(canvas, paint, 23, 20, 2, 6, whiteShirt)
        // Red Bowtie
        fillRect(canvas, paint, 23, 20, 2, 1, redBowTie)

        // Black sleeves with white cuffs
        fillRect(canvas, paint, 44, 20, 4, 10, tuxBlack)
        fillRect(canvas, paint, 44, 30, 4, 2, whiteShirt)
        fillRect(canvas, paint, 36, 52, 4, 10, tuxBlack)
        fillRect(canvas, paint, 36, 62, 4, 2, whiteShirt)

        // Black pants & dress shoes
        fillRect(canvas, paint, 4, 20, 4, 12, tuxBlack)
        fillRect(canvas, paint, 20, 52, 4, 12, tuxBlack)
    }

    private fun drawArcticExplorer(canvas: Canvas, paint: Paint) {
        val parkaWhite = Color.rgb(236, 239, 241)
        val iceBlue = Color.rgb(2, 136, 209)
        val furBrown = Color.rgb(141, 110, 99)

        drawAlex(canvas, paint)

        // Fur-lined Hood
        fillRect(canvas, paint, 40, 8, 8, 8, parkaWhite)
        fillRect(canvas, paint, 41, 9, 6, 6, Color.TRANSPARENT)
        fillRect(canvas, paint, 40, 9, 1, 6, furBrown) // Fur trim left
        fillRect(canvas, paint, 47, 9, 1, 6, furBrown) // Fur trim right

        // Insulated Parka
        fillRect(canvas, paint, 20, 20, 8, 12, iceBlue)
        fillRect(canvas, paint, 23, 20, 2, 12, parkaWhite) // Zipper lining
        fillRect(canvas, paint, 44, 20, 3, 10, iceBlue)
        fillRect(canvas, paint, 44, 30, 3, 2, furBrown) // Fur cuffs
        fillRect(canvas, paint, 36, 52, 3, 10, iceBlue)
        fillRect(canvas, paint, 36, 62, 3, 2, furBrown)

        // Thermal snow pants
        fillRect(canvas, paint, 4, 20, 4, 12, parkaWhite)
        fillRect(canvas, paint, 20, 52, 4, 12, parkaWhite)
    }
}
