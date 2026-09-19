package com.example.content

import com.example.launcher.MinecraftContentManager

enum class ContentSource { MODRINTH, CURSEFORGE }

enum class ContentType(
    val title: String,
    val projectType: String?,
    val kind: MinecraftContentManager.Kind
) {
    MOD("Mods", "mod", MinecraftContentManager.Kind.MOD),
    MODPACK("Modpacks", "modpack", MinecraftContentManager.Kind.MODPACK),
    SHADER("Shaders", "shader", MinecraftContentManager.Kind.SHADER),
    RESOURCE_PACK("Resource Packs", "resourcepack", MinecraftContentManager.Kind.RESOURCE_PACK),
    WORLD("Worlds", null, MinecraftContentManager.Kind.WORLD)
}

data class ContentItem(
    val id: String,
    val type: ContentType,
    val name: String,
    val description: String,
    val iconUrl: String?,
    val versions: List<String>,
    val loaders: List<String>,
    val categories: List<String>,
    val downloads: Long,
    val isLocal: Boolean = false,
    val localFileName: String? = null
)

data class ContentPage(
    val items: List<ContentItem>,
    val offset: Int,
    val hasMore: Boolean
)
