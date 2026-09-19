package com.example.minecraft

import com.example.downloader.DownloadManager
import com.example.downloader.DownloadTask
import com.example.filesystem.MinecraftFileSystem
import com.example.logs.LauncherLogger
import com.example.runtime.JavaRuntimeManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.security.MessageDigest
import java.util.jar.JarFile
import java.util.zip.ZipFile
import java.util.zip.ZipEntry
import java.util.zip.ZipOutputStream

/**
 * Step 24: bootstrap Forge/NeoForge installer metadata without pretending that
 * the desktop installer itself is an Android-native runtime. The installer JAR
 * is downloaded, inspected, and its embedded launcher profile/version JSON is
 * materialized when available. Processor execution remains a separate step.
 */
data class ProcessorRunResult(
    val success: Boolean,
    val executed: Int,
    val skipped: Int,
    val error: String?,
    val installerFormat: String = "unknown"
)

enum class ForgeInstallerFormat {
    V1, V2, LEGACY_PROFILE, LEGACY_JAR_MOD, UNSUPPORTED
}

data class LoaderBootstrapResult(
    val success: Boolean,
    val loader: String,
    val minecraftVersion: String,
    val loaderVersion: String,
    val profileId: String,
    val installerFile: File?,
    val downloadedLibraries: Int,
    val processorsRequired: Boolean,
    val error: String? = null
)

class ForgeNeoForgeInstaller(
    private val fileSystem: MinecraftFileSystem,
    private val downloadManager: DownloadManager,
    private val okHttpClient: OkHttpClient,
    private val javaRuntimeManager: JavaRuntimeManager
) {
    suspend fun prepare(
        loader: String,
        minecraftVersion: String,
        loaderVersion: String
    ): LoaderBootstrapResult = withContext(Dispatchers.IO) {
        val normalized = loader.lowercase()
        if (normalized != "forge" && normalized != "neoforge") {
            return@withContext failure(loader, minecraftVersion, loaderVersion, "Unsupported loader: $loader")
        }

        try {
            val vanillaJar = fileSystem.getVersionJarFile(minecraftVersion)
            val vanillaJson = fileSystem.getVersionJsonFile(minecraftVersion)
            if (!vanillaJar.exists() || !vanillaJson.exists()) {
                throw IOException("Minecraft $minecraftVersion must be installed first")
            }

            val installerUrl = when (normalized) {
                "forge" -> "https://maven.minecraftforge.net/net/minecraftforge/forge/$loaderVersion/forge-$loaderVersion-installer.jar"
                else -> "https://maven.neoforged.net/releases/net/neoforged/neoforge/$loaderVersion/neoforge-$loaderVersion-installer.jar"
            }
            val installerDir = File(fileSystem.rootDir, "loaders/$normalized/$minecraftVersion/$loaderVersion").apply { mkdirs() }
            val installerFile = File(installerDir, "$normalized-$loaderVersion-installer.jar")

            val downloaded = downloadManager.downloadSingleFile(
                DownloadTask(installerUrl, installerFile, name = installerFile.name)
            )
            if (!downloaded) throw IOException("Failed to download $normalized installer $loaderVersion")

            val installerInfo = inspectInstaller(installerFile)
            if (installerInfo.format == ForgeInstallerFormat.LEGACY_JAR_MOD) {
                return@withContext installLegacyJarMod(
                    normalized, minecraftVersion, loaderVersion, installerFile, vanillaJar, vanillaJson
                )
            }
            if (installerInfo.format == ForgeInstallerFormat.UNSUPPORTED || installerInfo.profile == null) {
                throw IOException("Unsupported $normalized installer format: ${installerInfo.reason}")
            }
            val embedded = installerInfo.profile

            // Forge has had multiple installer/profile layouts. V1 stores the
            // launcher metadata under versionInfo; V2 commonly ships a separate
            // version.json. Normalize both into one launch profile here.
            val profileJson = embedded.optJSONObject("versionInfo")
                ?: embedded.optJSONObject("version")
                ?: embedded
            val profileId = profileJson.optString("id").ifBlank {
                "$normalized-$loaderVersion"
            }
            if (normalized == "forge" && profileId.isBlank()) {
                throw IOException("Forge installer did not provide a usable profile id")
            }

            // Keep the installer-generated metadata isolated from vanilla. The
            // launch pipeline can resolve inheritsFrom against the vanilla profile.
            val profileDir = fileSystem.getVersionDir(profileId)
            val profileFile = File(profileDir, "$profileId.json")
            profileFile.writeText(profileJson.toString(2))
            val profileJar = File(profileDir, "$profileId.jar")
            if (!profileJar.exists() || profileJar.length() != vanillaJar.length()) {
                vanillaJar.copyTo(profileJar, overwrite = true)
            }

            val libraries = mergedLibraries(embedded, profileJson)
            val tasks = mutableListOf<DownloadTask>()
            for (i in 0 until libraries.length()) {
                val lib = libraries.optJSONObject(i) ?: continue
                val name = lib.optString("name")
                if (name.isBlank()) continue
                val downloads = lib.optJSONObject("downloads")
                val artifact = downloads?.optJSONObject("artifact")
                val path = artifact?.optString("path")?.takeIf { it.isNotBlank() } ?: mavenPath(name)
                val url = artifact?.optString("url")?.takeIf { it.isNotBlank() }
                    ?: mavenBase(normalized) + path
                tasks += DownloadTask(
                    url = url,
                    destination = File(fileSystem.librariesDir, path),
                    expectedSha1 = artifact?.optString("sha1")?.takeIf { !it.isNullOrBlank() },
                    size = artifact?.optLong("size", 0L) ?: 0L,
                    name = name
                )
            }

            val uniqueTasks = tasks.distinctBy { it.destination.absolutePath }
            if (uniqueTasks.isNotEmpty() && !downloadManager.downloadQueue(uniqueTasks)) {
                throw IOException("One or more $normalized libraries failed to download")
            }

            val processorsRequired = hasProcessors(embedded)
            LauncherLogger.info(
                "Prepared $normalized $loaderVersion for Minecraft $minecraftVersion as $profileId; " +
                    "libraries=${uniqueTasks.size}, processorsRequired=$processorsRequired"
            )

            LoaderBootstrapResult(
                true, normalized, minecraftVersion, loaderVersion, profileId,
                installerFile, uniqueTasks.size, processorsRequired
            )
        } catch (e: Exception) {
            LauncherLogger.error("$normalized bootstrap failed: ${e.message}")
            failure(loader, minecraftVersion, loaderVersion, e.message ?: "Unknown error")
        }
    }


    /**
     * Executes Forge/NeoForge client processors from install_profile.json.
     * Processors are run only when declared outputs are missing or have a
     * different SHA-1. This mirrors the installer profile contract: Maven
     * coordinates become library paths and {TOKEN} values are resolved from
     * the profile data plus the Minecraft installation paths.
     */
    suspend fun runClientProcessors(
        bootstrap: LoaderBootstrapResult,
        javaMajor: Int
    ): ProcessorRunResult = withContext(Dispatchers.IO) {
        if (!bootstrap.success || bootstrap.installerFile == null) {
            return@withContext ProcessorRunResult(false, 0, 0, "Bootstrap must succeed first")
        }
        try {
            val runtime = javaRuntimeManager.ensureRuntime(javaMajor) { status ->
                LauncherLogger.info("Forge/NeoForge processor runtime: $status")
            }
            val profile = readNormalizedInstallProfile(bootstrap.installerFile)
                ?: throw IOException("No supported Forge/NeoForge install profile found")
            val processors = mergedProcessors(profile)
            if (processors.length() == 0) {
                return@withContext ProcessorRunResult(true, 0, 0, null)
            }

            val data = mutableMapOf<String, String>()
            val profileData = profile.optJSONObject("data")
            profileData?.keys()?.forEachRemaining { key ->
                val entry = profileData.opt(key)
                if (entry is JSONObject) {
                    val value = entry.optString("client")
                    if (value.isNotBlank()) data[key] = resolveDataValue(value, bootstrap.installerFile)
                }
            }
            data["SIDE"] = "client"
            data["MINECRAFT_VERSION"] = bootstrap.minecraftVersion
            data["MINECRAFT_JAR"] = fileSystem.getVersionJarFile(bootstrap.minecraftVersion).absolutePath
            data["ROOT"] = fileSystem.rootDir.absolutePath
            data["LIBRARY_DIR"] = fileSystem.librariesDir.absolutePath
            data["INSTALLER"] = bootstrap.installerFile.absolutePath

            // Extract installer-embedded Maven libraries and download missing ones.
            val libs = mergedLibraries(profile, profile.optJSONObject("versionInfo") ?: profile)
            val libTasks = mutableListOf<DownloadTask>()
            for (i in 0 until libs.length()) {
                val lib = libs.optJSONObject(i) ?: continue
                val name = lib.optString("name")
                if (name.isBlank()) continue
                val path = lib.optJSONObject("downloads")?.optJSONObject("artifact")?.optString("path")
                    ?.takeIf { it.isNotBlank() } ?: mavenPath(name)
                val destination = File(fileSystem.librariesDir, path)
                if (!destination.isFile) {
                    extractMavenArtifact(bootstrap.installerFile, path, destination)
                }
                if (!destination.isFile) {
                    val artifact = lib.optJSONObject("downloads")?.optJSONObject("artifact")
                    val url = artifact?.optString("url")?.takeIf { it.isNotBlank() }
                        ?: mavenBase(bootstrap.loader) + path
                    libTasks += DownloadTask(url, destination,
                        expectedSha1 = artifact?.optString("sha1")?.takeIf { it.isNotBlank() },
                        size = artifact?.optLong("size", 0L) ?: 0L,
                        name = name)
                }
            }
            if (libTasks.isNotEmpty() && !downloadManager.downloadQueue(libTasks)) {
                throw IOException("Failed to download processor libraries")
            }

            var executed = 0
            var skipped = 0
            for (i in 0 until processors.length()) {
                val proc = processors.optJSONObject(i) ?: continue
                val sides = proc.optJSONArray("sides")
                if (sides != null && (0 until sides.length()).none { sides.optString(it) == "client" }) continue
                val outputs = proc.optJSONObject("outputs") ?: JSONObject()
                if (outputsSatisfied(outputs, data)) {
                    skipped++
                    continue
                }
                val jarCoord = proc.optJSONObject("jar")?.optString("path")
                    ?: proc.optString("jar")
                val jarPath = resolveProcessorPath(jarCoord)
                if (!jarPath.isFile) throw IOException("Processor JAR missing: $jarCoord")
                val mainClass = JarFile(jarPath).use { jar ->
                    jar.manifest?.mainAttributes?.getValue("Main-Class")
                        ?: throw IOException("Processor JAR has no Main-Class: ${jarPath.name}")
                }
                val cp = mutableListOf(jarPath.absolutePath)
                val classpath = proc.optJSONArray("classpath") ?: JSONArray()
                for (j in 0 until classpath.length()) {
                    val coord = classpath.optString(j)
                    val cpFile = resolveProcessorPath(coord)
                    if (!cpFile.isFile) throw IOException("Processor dependency missing: $coord")
                    cp += cpFile.absolutePath
                }
                val args = mutableListOf<String>()
                val rawArgs = proc.optJSONArray("args") ?: JSONArray()
                for (j in 0 until rawArgs.length()) args += resolveProcessorArg(rawArgs.optString(j), data)

                val pb = ProcessBuilder(listOf(runtime.javaExecutable.absolutePath, "-cp", cp.joinToString(File.pathSeparator), mainClass) + args)
                    .directory(fileSystem.rootDir)
                    .redirectErrorStream(true)
                pb.environment()["JAVA_HOME"] = runtime.javaHome.absolutePath
                val process = pb.start()
                val output = process.inputStream.bufferedReader().readText()
                val exit = process.waitFor()
                LauncherLogger.info("Processor ${i + 1}/${processors.length()} exit=$exit${if (output.isNotBlank()) ": ${output.take(1200)}" else ""}")
                if (exit != 0) throw IOException("Processor ${i + 1} failed with exit code $exit")
                if (!outputsSatisfied(outputs, data)) throw IOException("Processor ${i + 1} completed but declared outputs are missing or invalid")
                executed++
            }
            ProcessorRunResult(true, executed, skipped, null)
        } catch (e: Exception) {
            LauncherLogger.error("Forge/NeoForge processor pipeline failed: ${e.message}")
            ProcessorRunResult(false, 0, 0, e.message ?: "Processor failure")
        }
    }

    private data class InstallerInspection(
        val format: ForgeInstallerFormat,
        val profile: JSONObject?,
        val reason: String
    )

    /** Detects the installer generation instead of assuming every Forge/NeoForge
     * installer is the newest processor layout. Forge documents substantial
     * differences across legacy versions, so the launcher treats unsupported
     * pre-profile installers explicitly rather than failing later with a vague error. */
    private fun inspectInstaller(installer: File): InstallerInspection = ZipFile(installer).use { zip ->
        val installEntry = zip.getEntry("install_profile.json")
        val versionEntry = zip.getEntry("version.json")
        if (installEntry == null && versionEntry == null) {
            val legacy = looksLikeLegacyJarMod(zip)
            return@use if (legacy) {
                InstallerInspection(ForgeInstallerFormat.LEGACY_JAR_MOD, null,
                    "legacy Forge jar-mod/universal installer without launcher profile")
            } else {
                InstallerInspection(ForgeInstallerFormat.UNSUPPORTED, null,
                    "installer has neither install_profile.json nor version.json")
            }
        }
        val install = installEntry?.let { zip.getInputStream(it).bufferedReader().use { r -> JSONObject(r.readText()) } }
        val version = versionEntry?.let { zip.getInputStream(it).bufferedReader().use { r -> JSONObject(r.readText()) } }
        when {
            install != null && version != null -> InstallerInspection(ForgeInstallerFormat.V2, install, "install_profile.json + version.json")
            install != null -> {
                val hasVersionInfo = install.has("versionInfo") || install.has("version")
                if (hasVersionInfo) InstallerInspection(ForgeInstallerFormat.V1, install, "install_profile.json/versionInfo")
                else InstallerInspection(ForgeInstallerFormat.LEGACY_PROFILE, install, "install_profile.json")
            }
            else -> InstallerInspection(ForgeInstallerFormat.V2, version, "version.json")
        }
    }


    /**
     * Older Forge releases predate launcher profiles. Their installer/universal
     * JAR is effectively a set of classes/resources that must be overlaid onto
     * the vanilla client JAR. We recognize those archives conservatively by
     * looking for Forge's package namespace and installer markers.
     */
    private fun looksLikeLegacyJarMod(zip: ZipFile): Boolean {
        var forgeClasses = 0
        var minecraftPatchMarkers = 0
        val entries = zip.entries()
        while (entries.hasMoreElements()) {
            val name = entries.nextElement().name
            if (name.startsWith("net/minecraftforge/")) forgeClasses++
            if (name.startsWith("cpw/mods/")) minecraftPatchMarkers++
            if (name == "META-INF/MANIFEST.MF" || name == "forge_at.cfg" || name == "forgeversion.properties" || name.startsWith("META-INF/services/")) minecraftPatchMarkers++
            if (forgeClasses >= 3 && minecraftPatchMarkers > 0) return true
        }
        return forgeClasses >= 8
    }

    private suspend fun installLegacyJarMod(
        loader: String,
        minecraftVersion: String,
        loaderVersion: String,
        installerFile: File,
        vanillaJar: File,
        vanillaJson: File
    ): LoaderBootstrapResult {
        if (loader != "forge") {
            throw IOException("Legacy jar-mod installers are supported only for Forge; NeoForge requires a profile/processor installer")
        }

        val profileId = "${minecraftVersion}-forge-$loaderVersion-legacy"
        val profileDir = fileSystem.getVersionDir(profileId)
        val profileFile = File(profileDir, "$profileId.json")
        val profileJar = File(profileDir, "$profileId.jar")

        patchLegacyForgeJar(vanillaJar, installerFile, profileJar)

        val base = JSONObject(vanillaJson.readText())
        base.put("id", profileId)
        base.put("inheritsFrom", minecraftVersion)
        // Old Forge jar-mod versions use the vanilla Minecraft main class; the
        // Forge classes are injected into the client JAR itself.
        val downloads = base.optJSONObject("downloads") ?: JSONObject().also { base.put("downloads", it) }
        val client = downloads.optJSONObject("client") ?: JSONObject().also { downloads.put("client", it) }
        client.put("size", profileJar.length())
        client.put("sha1", sha1(profileJar))
        profileFile.writeText(base.toString(2))

        LauncherLogger.info("Installed legacy Forge jar-mod $loaderVersion as $profileId")
        return LoaderBootstrapResult(
            success = true, loader = loader, minecraftVersion = minecraftVersion,
            loaderVersion = loaderVersion, profileId = profileId, installerFile = installerFile,
            downloadedLibraries = 0, processorsRequired = false
        )
    }

    private fun patchLegacyForgeJar(vanillaJar: File, forgeJar: File, output: File) {
        val temp = File(output.parentFile, output.name + ".tmp")
        temp.delete()
        ZipFile(forgeJar).use { forge ->
            ZipFile(vanillaJar).use { vanilla ->
                ZipOutputStream(temp.outputStream().buffered()).use { out ->
                    val entries = vanilla.entries()
                    while (entries.hasMoreElements()) {
                        val entry = entries.nextElement()
                        val name = entry.name
                        if (name.startsWith("META-INF/") &&
                            (name.endsWith(".SF", true) || name.endsWith(".RSA", true) || name.endsWith(".DSA", true))) continue
                        if (forge.getEntry(name) != null && !name.startsWith("META-INF/")) {
                            continue
                        }
                        val copy = ZipEntry(name)
                        copy.time = entry.time
                        out.putNextEntry(copy)
                        vanilla.getInputStream(entry).use { it.copyTo(out) }
                        out.closeEntry()
                    }

                    val forgeEntries = forge.entries()
                    while (forgeEntries.hasMoreElements()) {
                        val entry = forgeEntries.nextElement()
                        val name = entry.name
                        if (name == "META-INF/MANIFEST.MF" ||
                            (name.startsWith("META-INF/") &&
                                (name.endsWith(".SF", true) || name.endsWith(".RSA", true) || name.endsWith(".DSA", true)))) continue
                        if (name == "" || name.endsWith("/")) continue
                        val copy = ZipEntry(name)
                        copy.time = entry.time
                        out.putNextEntry(copy)
                        forge.getInputStream(entry).use { it.copyTo(out) }
                        out.closeEntry()
                    }
                }
            }
        }
        if (!temp.renameTo(output)) {
            temp.copyTo(output, overwrite = true)
            temp.delete()
        }
    }

    private fun readNormalizedInstallProfile(installer: File): JSONObject? = ZipFile(installer).use { zip ->
        val install = zip.getEntry("install_profile.json")?.let {
            zip.getInputStream(it).bufferedReader().use { r -> JSONObject(r.readText()) }
        }
        val version = zip.getEntry("version.json")?.let {
            zip.getInputStream(it).bufferedReader().use { r -> JSONObject(r.readText()) }
        }
        when {
            install == null -> version
            version == null -> install
            else -> {
                // Preserve installer-only fields (processors/data) while making
                // version.json's launcher metadata available to the same pipeline.
                val out = JSONObject(install.toString())
                if (!out.has("versionInfo")) out.put("versionInfo", version)
                if (!out.has("libraries") && version.has("libraries")) out.put("libraries", version.getJSONArray("libraries"))
                out
            }
        }
    }

    private fun mergedProcessors(profile: JSONObject): JSONArray {
        val direct = profile.optJSONArray("processors")
        if (direct != null) return direct
        return profile.optJSONObject("versionInfo")?.optJSONArray("processors") ?: JSONArray()
    }

    private fun mergedLibraries(primary: JSONObject, secondary: JSONObject): JSONArray {
        val out = JSONArray()
        val seen = HashSet<String>()
        fun append(source: JSONObject?) {
            val libs = source?.optJSONArray("libraries") ?: return
            for (i in 0 until libs.length()) {
                val lib = libs.optJSONObject(i) ?: continue
                val name = lib.optString("name")
                if (name.isNotBlank() && seen.add(name)) out.put(lib)
            }
        }
        append(primary)
        append(secondary)
        return out
    }

    private fun readInstallProfile(installer: File): JSONObject? = ZipFile(installer).use { zip ->
        val entry = zip.getEntry("install_profile.json") ?: return@use null
        zip.getInputStream(entry).bufferedReader().use { JSONObject(it.readText()) }
    }

    private fun resolveDataValue(value: String, installer: File): String {
        if (value.startsWith("[") && value.endsWith("]")) return resolveProcessorPath(value).absolutePath
        if (value.startsWith("'") && value.endsWith("'")) return value.substring(1, value.length - 1)
        ZipFile(installer).use { zip ->
            val entry = zip.getEntry(value) ?: return value
            val out = File(fileSystem.rootDir, "forge-installer-data/$value").canonicalFile
            val root = File(fileSystem.rootDir, "forge-installer-data").canonicalFile
            if (!out.path.startsWith(root.path + File.separator)) throw IOException("Unsafe installer data path")
            out.parentFile?.mkdirs()
            zip.getInputStream(entry).use { input -> out.outputStream().use { input.copyTo(it) } }
            return out.absolutePath
        }
    }

    private fun resolveProcessorArg(raw: String, data: Map<String, String>): String {
        if (raw.startsWith("[") && raw.endsWith("]")) return resolveProcessorPath(raw).absolutePath
        return raw.replace(Regex("\\{([A-Za-z0-9_-]+)\\}")) { data[it.groupValues[1]] ?: "" }
    }

    private fun resolveProcessorPath(token: String): File {
        val coord = token.removePrefix("[").removeSuffix("]")
        val clean = coord.removePrefix("maven:")
        return File(fileSystem.librariesDir, mavenPath(clean))
    }

    private fun extractMavenArtifact(installer: File, path: String, destination: File) {
        ZipFile(installer).use { zip ->
            val entry = zip.getEntry("maven/$path") ?: return
            destination.parentFile?.mkdirs()
            zip.getInputStream(entry).use { input -> destination.outputStream().use { input.copyTo(it) } }
        }
    }

    private fun sha1(file: File): String {
        val md = MessageDigest.getInstance("SHA-1")
        file.inputStream().use { input ->
            val buffer = ByteArray(64 * 1024)
            while (true) {
                val n = input.read(buffer)
                if (n <= 0) break
                md.update(buffer, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }
    private fun outputsSatisfied(outputs: JSONObject, data: Map<String, String>): Boolean {
        if (outputs.length() == 0) return false
        val keys = outputs.keys()
        while (keys.hasNext()) {
            val rawKey = keys.next()
            val rawExpected = outputs.optString(rawKey)
            val path = resolveProcessorArg(rawKey, data).trim('"', '\'')
            val file = File(path)
            if (!file.isFile) return false
            if (rawExpected.isNotBlank() && !rawExpected.startsWith("{")) {
                if (!sha1(file).equals(rawExpected.trim('\''), ignoreCase = true)) return false
            }
        }
        return true
    }

    private fun sha1(file: File): String {
        val md = MessageDigest.getInstance("SHA-1")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val n = input.read(buffer)
                if (n <= 0) break
                md.update(buffer, 0, n)
            }
        }
        return md.digest().joinToString("") { "%02x".format(it) }
    }

    private fun readEmbeddedProfile(installer: File): JSONObject? {
        ZipFile(installer).use { zip ->
            val names = listOf("install_profile.json", "version.json", "data/install_profile.json")
            for (name in names) {
                val entry = zip.getEntry(name) ?: continue
                zip.getInputStream(entry).bufferedReader().use { return JSONObject(it.readText()) }
            }
        }
        return null
    }

    private fun hasProcessors(profile: JSONObject): Boolean {
        val processors = profile.optJSONArray("processors")
        if (processors != null && processors.length() > 0) return true
        val versionInfo = profile.optJSONObject("versionInfo")
        return versionInfo?.optJSONArray("processors")?.length()?.let { it > 0 } ?: false
    }

    private fun mavenBase(loader: String): String = when (loader) {
        "forge" -> "https://maven.minecraftforge.net/"
        else -> "https://maven.neoforged.net/releases/"
    }

    private fun mavenPath(name: String): String {
        val parts = name.split(":")
        if (parts.size < 3) throw IOException("Invalid Maven coordinate: $name")
        val group = parts[0].replace('.', '/')
        val artifact = parts[1]
        val versionExt = parts[2].split("@", limit = 2)
        val version = versionExt[0]
        val ext = if (versionExt.size == 2) versionExt[1] else "jar"
        val classifier = if (parts.size >= 4) "-${parts[3]}" else ""
        return "$group/$artifact/$version/$artifact-$version$classifier.$ext"
    }

    private fun failure(loader: String, mc: String, version: String, error: String) =
        LoaderBootstrapResult(false, loader.lowercase(), mc, version, "$loader-$version", null, 0, false, error)
}
