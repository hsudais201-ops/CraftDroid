package com.example.launcher

/** Supported Java mod-loader families and safe instance-directory layout. */
object MinecraftLoaderProfile {
    enum class Loader { VANILLA, FABRIC, FORGE, NEOFORGE, QUILT }

    data class Profile(
        val loader: Loader,
        val displayName: String,
        val modsDirectory: String = "mods",
        val configDirectory: String = "config",
        val resourcePacksDirectory: String = "resourcepacks",
        val shaderPacksDirectory: String = "shaderpacks"
    )

    fun parse(raw: String?): Loader {
        return when (raw?.trim()?.lowercase()) {
            "fabric" -> Loader.FABRIC
            "forge" -> Loader.FORGE
            "neoforge", "neo-forge" -> Loader.NEOFORGE
            "quilt" -> Loader.QUILT
            else -> Loader.VANILLA
        }
    }

    fun profile(raw: String?): Profile = when (val loader = parse(raw)) {
        Loader.VANILLA -> Profile(loader, "Vanilla")
        Loader.FABRIC -> Profile(loader, "Fabric")
        Loader.FORGE -> Profile(loader, "Forge")
        Loader.NEOFORGE -> Profile(loader, "NeoForge")
        Loader.QUILT -> Profile(loader, "Quilt")
    }
}
