package com.example.minecraft

import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File

data class ModItem(
    val name: String,
    val fileName: String,
    val sizeBytes: Long,
    val isEnabled: Boolean
)

data class ResourcePackItem(
    val name: String,
    val fileName: String,
    val sizeBytes: Long,
    val isEnabled: Boolean
)

class ModManager(private val fileSystem: MinecraftFileSystem) {

    suspend fun getInstalledMods(): List<ModItem> = withContext(Dispatchers.IO) {
        val modsDir = fileSystem.modsDir
        val list = mutableListOf<ModItem>()
        modsDir.listFiles()?.forEach { file ->
            if (file.isFile && (file.name.endsWith(".jar") || file.name.endsWith(".jar.disabled"))) {
                list.add(
                    ModItem(
                        name = file.name.removeSuffix(".disabled").removeSuffix(".jar"),
                        fileName = file.name,
                        sizeBytes = file.length(),
                        isEnabled = !file.name.endsWith(".disabled")
                    )
                )
            }
        }
        list
    }

    suspend fun toggleMod(mod: ModItem): Boolean = withContext(Dispatchers.IO) {
        val file = File(fileSystem.modsDir, mod.fileName)
        if (!file.exists()) return@withContext false

        val newFile = if (mod.isEnabled) {
            File(fileSystem.modsDir, "${mod.fileName}.disabled")
        } else {
            File(fileSystem.modsDir, mod.fileName.removeSuffix(".disabled"))
        }
        file.renameTo(newFile)
    }

    suspend fun deleteMod(mod: ModItem): Boolean = withContext(Dispatchers.IO) {
        val file = File(fileSystem.modsDir, mod.fileName)
        file.delete()
    }

    suspend fun getInstalledResourcePacks(): List<ResourcePackItem> = withContext(Dispatchers.IO) {
        val rpDir = fileSystem.resourcePacksDir
        val list = mutableListOf<ResourcePackItem>()
        rpDir.listFiles()?.forEach { file ->
            if (file.isFile && (file.name.endsWith(".zip") || file.name.endsWith(".zip.disabled"))) {
                list.add(
                    ResourcePackItem(
                        name = file.name.removeSuffix(".disabled").removeSuffix(".zip"),
                        fileName = file.name,
                        sizeBytes = file.length(),
                        isEnabled = !file.name.endsWith(".disabled")
                    )
                )
            }
        }
        list
    }

    suspend fun toggleResourcePack(rp: ResourcePackItem): Boolean = withContext(Dispatchers.IO) {
        val file = File(fileSystem.resourcePacksDir, rp.fileName)
        if (!file.exists()) return@withContext false

        val newFile = if (rp.isEnabled) {
            File(fileSystem.resourcePacksDir, "${rp.fileName}.disabled")
        } else {
            File(fileSystem.resourcePacksDir, rp.fileName.removeSuffix(".disabled"))
        }
        file.renameTo(newFile)
    }
}
