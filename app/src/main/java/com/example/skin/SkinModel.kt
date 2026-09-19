package com.example.skin

enum class SkinModel(val id: String, val label: String, val armWidth: Int) {
    CLASSIC("classic", "Classic (Steve / 4px arms)", 4),
    SLIM("slim", "Slim (Alex / 3px arms)", 3);

    companion object {
        fun fromId(id: String?): SkinModel {
            return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: CLASSIC
        }
    }
}

data class SkinPreset(
    val id: String,
    val name: String,
    val model: SkinModel,
    val description: String,
    val category: String,
    val primaryColorHex: Long,
    val secondaryColorHex: Long
)

object SkinPresets {
    val presets = listOf(
        SkinPreset(
            id = "steve",
            name = "Classic Steve",
            model = SkinModel.CLASSIC,
            description = "The iconic Minecraft hero with cyan tee and blue jeans.",
            category = "Classic",
            primaryColorHex = 0xFF00ACC1, // Cyan
            secondaryColorHex = 0xFF1565C0 // Blue jeans
        ),
        SkinPreset(
            id = "alex",
            name = "Classic Alex",
            model = SkinModel.SLIM,
            description = "The agile adventurer with green tunic and brown boots.",
            category = "Classic",
            primaryColorHex = 0xFF558B2F, // Green tunic
            secondaryColorHex = 0xFFE65100 // Orange hair
        ),
        SkinPreset(
            id = "cyber_steve",
            name = "Cyberpunk Steve",
            model = SkinModel.CLASSIC,
            description = "Neon augmented explorer with cyan visor and tech vest.",
            category = "Sci-Fi",
            primaryColorHex = 0xFF00E5FF, // Neon cyan
            secondaryColorHex = 0xFF212121 // Dark carbon
        ),
        SkinPreset(
            id = "diamond_knight",
            name = "Diamond Paladin",
            model = SkinModel.CLASSIC,
            description = "Shining diamond-plated battle armor with lapis highlights.",
            category = "Medieval",
            primaryColorHex = 0xFF4DD0E1, // Diamond
            secondaryColorHex = 0xFF0D47A1 // Deep lapis
        ),
        SkinPreset(
            id = "creeper_hoodie",
            name = "Creeper Hoodie",
            model = SkinModel.CLASSIC,
            description = "Casual modern look with an embroidered green creeper face.",
            category = "Casual",
            primaryColorHex = 0xFF4CAF50, // Creeper green
            secondaryColorHex = 0xFF263238 // Dark denim
        ),
        SkinPreset(
            id = "ender_sorcerer",
            name = "Ender Sorcerer",
            model = SkinModel.SLIM,
            description = "Mystical obsidian robe with glowing purple rift eyes.",
            category = "Fantasy",
            primaryColorHex = 0xFF9C27B0, // Ender purple
            secondaryColorHex = 0xFF1A237E // Midnight
        ),
        SkinPreset(
            id = "netherite_pioneer",
            name = "Netherite Pioneer",
            model = SkinModel.CLASSIC,
            description = "Heavy netherite alloy suit crafted for Nether survival.",
            category = "Survival",
            primaryColorHex = 0xFF37474F, // Dark Netherite
            secondaryColorHex = 0xFFFFB300 // Gold trim
        ),
        SkinPreset(
            id = "redstone_engineer",
            name = "Redstone Engineer",
            model = SkinModel.SLIM,
            description = "Brass goggles, leather apron, and powered redstone wiring.",
            category = "Tech",
            primaryColorHex = 0xFFE53935, // Redstone
            secondaryColorHex = 0xFF795548 // Leather brown
        ),
        SkinPreset(
            id = "tuxedo_agent",
            name = "Tuxedo Agent",
            model = SkinModel.CLASSIC,
            description = "Formal black tuxedo suit, white shirt, and scarlet bow tie.",
            category = "Formal",
            primaryColorHex = 0xFF212121, // Black suit
            secondaryColorHex = 0xFFD32F2F // Red bow
        ),
        SkinPreset(
            id = "arctic_explorer",
            name = "Arctic Explorer",
            model = SkinModel.SLIM,
            description = "Insulated fur-lined thermal parka with snow goggles.",
            category = "Adventure",
            primaryColorHex = 0xFFECEFF1, // Snow white / fur
            secondaryColorHex = 0xFF0288D1 // Ice blue
        )
    )

    fun findById(id: String): SkinPreset? {
        return presets.firstOrNull { it.id == id }
    }
}
