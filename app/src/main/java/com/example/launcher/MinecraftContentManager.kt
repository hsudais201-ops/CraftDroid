package com.example.launcher

import android.content.Context
import com.example.filesystem.MinecraftFileSystem
import java.io.File
import java.io.FileOutputStream
import java.util.zip.ZipFile

object MinecraftContentManager {
    enum class Kind { MOD, MODPACK, SHADER, RESOURCE_PACK, WORLD }

    fun list(context: Context, kind: Kind): List<File> {
        val fs = MinecraftFileSystem(context)
        val dir = when (kind) {
            Kind.MOD -> fs.modsDir
            Kind.MODPACK -> File(fs.rootDir, "modpacks").apply { mkdirs() }
            Kind.SHADER -> fs.shaderPacksDir
            Kind.RESOURCE_PACK -> fs.resourcePacksDir
            Kind.WORLD -> fs.savesDir
        }
        return dir.listFiles()?.filter { it.exists() }?.sortedBy { it.name.lowercase() }.orEmpty()
    }

    fun importFile(context: Context, kind: Kind, source: File, originalName: String): File {
        val fs = MinecraftFileSystem(context)
        val destinationDir = when (kind) {
            Kind.MOD -> fs.modsDir
            Kind.SHADER -> fs.shaderPacksDir
            Kind.RESOURCE_PACK -> fs.resourcePacksDir
            Kind.MODPACK -> File(fs.rootDir, "modpacks").apply { mkdirs() }
            Kind.WORLD -> fs.savesDir
        }.apply { mkdirs() }
        val safeName = originalName.substringAfterLast('/').substringAfterLast('\\').ifBlank { source.name }
        val destination = File(destinationDir, safeName)
        source.copyTo(destination, overwrite = true)
        return destination
    }

    fun importArchive(context: Context, kind: Kind, archive: File): File {
        val fs = MinecraftFileSystem(context)
        return when (kind) {
            Kind.WORLD -> {
                val base = fs.savesDir
                ZipFile(archive).use { zip ->
                    val root = zip.entries().asSequence().map { it.name.substringBefore('/') }.firstOrNull().orEmpty()
                    val worldName = root.ifBlank { archive.nameWithoutExtension }
                    val target = safeDirectory(base, worldName)
                    extractZip(zip, target)
                    target
                }
            }
            else -> importFile(context, kind, archive, archive.name)
        }
    }

    private fun safeDirectory(parent: File, name: String): File {
        val safe = name.replace(Regex("[^A-Za-z0-9._ -]"), "_").trim().ifBlank { "world" }
        return File(parent, safe).apply { mkdirs() }
    }

    private fun extractZip(zip: ZipFile, destination: File) {
        val base = destination.canonicalFile
        val entries = zip.entries()
        while (entries.hasMoreElements()) {
            val entry = entries.nextElement()
            val target = File(destination, entry.name).canonicalFile
            require(target.path == base.path || target.path.startsWith(base.path + File.separator)) {
                "Unsafe archive entry: ${entry.name}"
            }
            if (entry.isDirectory) {
                target.mkdirs()
            } else {
                target.parentFile?.mkdirs()
                zip.getInputStream(entry).use { input ->
                    FileOutputStream(target).use { output -> input.copyTo(output) }
                }
            }
        }
    }
}

data class ModpackInstallResult(val instanceDirectory: File)

object MinecraftModpackManager {
    suspend fun install(context: Context, archive: File): ModpackInstallResult {
        val fs = MinecraftFileSystem(context)
        val modpacksDir = File(fs.rootDir, "modpacks").apply { mkdirs() }
        val index = org.json.JSONObject(
            ZipFile(archive).use { zip ->
                val entry = zip.getEntry("modrinth.index.json") ?: error("Not a Modrinth .mrpack archive")
                zip.getInputStream(entry).bufferedReader().use { it.readText() }
            }
        )
        val name = index.optString("name").ifBlank { archive.nameWithoutExtension }
            .replace(Regex("[^A-Za-z0-9._ -]"), "_")
        val instance = File(modpacksDir, name).apply { mkdirs() }

        ZipFile(archive).use { zip ->
            val overrides = zip.entries().asSequence().filter { it.name.startsWith("overrides/") }
            val base = instance.canonicalFile
            overrides.forEach { entry ->
                val relative = entry.name.removePrefix("overrides/")
                if (relative.isBlank()) return@forEach
                val target = File(instance, relative).canonicalFile
                require(target.path == base.path || target.path.startsWith(base.path + File.separator)) {
                    "Unsafe modpack entry"
                }
                if (entry.isDirectory) target.mkdirs() else {
                    target.parentFile?.mkdirs()
                    zip.getInputStream(entry).use { input ->
                        FileOutputStream(target).use { output -> input.copyTo(output) }
                    }
                }
            }
        }

        archive.copyTo(File(instance, "pack.mrpack"), overwrite = true)
        File(instance, "manifest.json").writeText(index.toString(2))
        return ModpackInstallResult(instance)
    }
}
