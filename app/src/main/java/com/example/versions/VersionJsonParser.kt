package com.example.versions

import android.os.Build
import org.json.JSONArray
import org.json.JSONObject

class VersionJsonParser {

    fun parseVersionDetail(rawJson: String): VersionDetail {
        val root = JSONObject(rawJson)
        val id = root.getString("id")
        val mainClass = root.optString("mainClass", "net.minecraft.client.main.Main")

        // 1. Java Version info
        val javaObj = root.optJSONObject("javaVersion")
        val javaInfo = if (javaObj != null) {
            JavaVersionInfo(
                component = javaObj.optString("component", "java-runtime-gamma"),
                majorVersion = javaObj.optInt("majorVersion", inferJavaVersion(id))
            )
        } else {
            JavaVersionInfo(majorVersion = inferJavaVersion(id))
        }

        // 2. Client download
        val downloads = root.getJSONObject("downloads")
        val clientJson = downloads.getJSONObject("client")
        val clientDownload = VersionDownload(
            sha1 = clientJson.getString("sha1"),
            size = clientJson.getLong("size"),
            url = clientJson.getString("url")
        )

        // 3. Asset Index
        val assetIndexJson = root.getJSONObject("assetIndex")
        val assetIndex = AssetIndexInfo(
            id = assetIndexJson.getString("id"),
            sha1 = assetIndexJson.getString("sha1"),
            size = assetIndexJson.getLong("size"),
            totalSize = assetIndexJson.optLong("totalSize", assetIndexJson.getLong("size")),
            url = assetIndexJson.getString("url")
        )

        // 4. Libraries
        val libraries = mutableListOf<Library>()
        val libArray = root.optJSONArray("libraries") ?: JSONArray()
        for (i in 0 until libArray.length()) {
            val libObj = libArray.getJSONObject(i)
            val parsedLib = parseLibrary(libObj)
            if (parsedLib != null) {
                libraries.add(parsedLib)
            }
        }

        // 5. Assets/logging metadata
        val assets = root.optString("assets", null)
        val logging = root.optJSONObject("logging")?.optJSONObject("client")?.let { client ->
            val file = client.optJSONObject("file")
            val id = client.optString("argument", "${path}")
                .removePrefix("${")
                .removeSuffix("}")
                .ifBlank { "client" }
            if (file != null) {
                LoggingConfig(
                    clientFileId = id,
                    clientFilePath = file.optString("id", ""),
                    clientFileSha1 = file.optString("sha1", null)
                )
            } else null
        }

        // 6. Arguments
        val jvmArgs = mutableListOf<Any>()
        val gameArgs = mutableListOf<Any>()
        var legacyArgs: String? = null

        val argumentsObj = root.optJSONObject("arguments")
        if (argumentsObj != null) {
            val jvmArr = argumentsObj.optJSONArray("jvm")
            if (jvmArr != null) {
                for (i in 0 until jvmArr.length()) {
                    jvmArgs.add(jvmArr.get(i))
                }
            }
            val gameArr = argumentsObj.optJSONArray("game")
            if (gameArr != null) {
                for (i in 0 until gameArr.length()) {
                    gameArgs.add(gameArr.get(i))
                }
            }
        } else {
            legacyArgs = if (root.has("minecraftArguments")) root.getString("minecraftArguments") else null
        }

        return VersionDetail(
            id = id,
            mainClass = mainClass,
            javaVersion = javaInfo,
            clientDownload = clientDownload,
            assetIndex = assetIndex,
            libraries = libraries,
            jvmArguments = jvmArgs,
            gameArguments = gameArgs,
            legacyMinecraftArguments = legacyArgs,
            assets = assets,
            logging = logging
        )
    }

    private fun parseLibrary(obj: JSONObject): Library? {
        val name = obj.getString("name")
        val rules = parseRules(obj.optJSONArray("rules"))

        // Check if rules allow on Android (Linux environment)
        if (!evaluateRules(rules)) {
            return null
        }

        var artifact: LibraryArtifact? = null
        val downloads = obj.optJSONObject("downloads")

        if (downloads != null) {
            val artObj = downloads.optJSONObject("artifact")
            if (artObj != null) {
                artifact = LibraryArtifact(
                    path = artObj.getString("path"),
                    sha1 = artObj.getString("sha1"),
                    size = artObj.getLong("size"),
                    url = artObj.getString("url")
                )
            }
        }

        // Fallback: construct standard maven path if no explicit downloads block
        if (artifact == null && !name.isNullOrBlank()) {
            artifact = mavenNameToArtifact(name, obj.optString("url", "https://libraries.minecraft.net/"))
        }

        // Parse natives
        var nativesClassifier: String? = null
        var nativesArtifact: LibraryArtifact? = null
        val nativesObj = obj.optJSONObject("natives")
        if (nativesObj != null) {
            val linuxKey = if (nativesObj.has("linux")) nativesObj.getString("linux") else null
            if (linuxKey != null) {
                val resolvedClassifier = resolveArchTemplate(linuxKey)
                nativesClassifier = resolvedClassifier

                val classifiers = downloads?.optJSONObject("classifiers")
                val nativeJson = classifiers?.optJSONObject(resolvedClassifier)
                if (nativeJson != null) {
                    nativesArtifact = LibraryArtifact(
                        path = nativeJson.getString("path"),
                        sha1 = nativeJson.getString("sha1"),
                        size = nativeJson.getLong("size"),
                        url = nativeJson.getString("url")
                    )
                }
            }
        }

        val extractExcludes = mutableListOf<String>()
        val extractObj = obj.optJSONObject("extract")
        val excludesArr = extractObj?.optJSONArray("exclude")
        if (excludesArr != null) {
            for (j in 0 until excludesArr.length()) {
                extractExcludes.add(excludesArr.getString(j))
            }
        }

        return Library(
            name = name,
            artifact = artifact,
            nativesClassifier = nativesClassifier,
            nativesArtifact = nativesArtifact,
            rules = rules,
            extractExcludes = extractExcludes
        )
    }

    private fun parseRules(rulesArray: JSONArray?): List<LibraryRule> {
        if (rulesArray == null) return emptyList()
        val list = mutableListOf<LibraryRule>()
        for (i in 0 until rulesArray.length()) {
            val r = rulesArray.getJSONObject(i)
            val action = r.getString("action")
            val os = r.optJSONObject("os")
            list.add(
                LibraryRule(
                    action = action,
                    osName = if (os?.has("name") == true) os.getString("name") else null,
                    osVersion = if (os?.has("version") == true) os.getString("version") else null,
                    osArch = if (os?.has("arch") == true) os.getString("arch") else null
                )
            )
        }
        return list
    }

    /**
     * Evaluates Mojang rule list against Android (Linux kernel / Android target).
     */
    fun evaluateRules(rules: List<LibraryRule>): Boolean {
        if (rules.isEmpty()) return true

        // Mojang's rule lists are ordered: a matching rule replaces the current
        // decision. Android presents itself as Linux to Java, so Linux rules are
        // applicable, while Windows/macOS rules are ignored.
        var allowed = false
        for (rule in rules) {
            if (ruleMatchesCurrentPlatform(rule)) {
                allowed = rule.action.equals("allow", ignoreCase = true)
            }
        }
        return allowed
    }

    private fun ruleMatchesCurrentPlatform(rule: LibraryRule): Boolean {
        val osMatches = when (rule.osName?.lowercase()) {
            null, "linux", "android" -> true
            else -> false
        }
        if (!osMatches) return false

        val requestedArch = rule.osArch?.lowercase() ?: return true
        val current = Build.SUPPORTED_ABIS.firstOrNull()?.lowercase() ?: ""
        return when (requestedArch) {
            "x86_64", "amd64" -> current.contains("x86_64") || current.contains("amd64")
            "x86" -> current == "x86" || current == "i686"
            "aarch64", "arm64" -> current.contains("arm64") || current.contains("aarch64")
            "arm", "arm32", "armeabi-v7a" -> current.contains("armeabi") || current.contains("armv7")
            else -> true
        }
    }

    private fun resolveArchTemplate(classifier: String): String {
        val is64Bit = Build.SUPPORTED_ABIS.firstOrNull()?.let {
            it.contains("64", ignoreCase = true) || it.contains("aarch64", ignoreCase = true)
        } == true
        return classifier.replace("\${arch}", if (is64Bit) "64" else "32")
    }

    private fun mavenNameToArtifact(name: String, baseUrl: String = "https://libraries.minecraft.net/"): LibraryArtifact {
        // Format: groupId:artifactId:version[:classifier]@ext
        val parts = name.split(":")
        val group = parts[0].replace('.', '/')
        val artifact = parts[1]
        val versionAndMore = parts[2].split("@")
        val version = versionAndMore[0]
        val ext = if (versionAndMore.size > 1) versionAndMore[1] else "jar"
        val classifier = if (parts.size > 3) "-${parts[3]}" else ""
        val filename = "$artifact-$version$classifier.$ext"
        val path = "$group/$artifact/$version/$filename"
        val normalizedBase = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val url = "$normalizedBase$path"
        return LibraryArtifact(path = path, sha1 = "", size = 0L, url = url)
    }

    private fun inferJavaVersion(versionId: String): Int {
        val normalized = versionId.trim().removePrefix("v")
        val parts = normalized.split('.', '-', '+').mapNotNull { it.toIntOrNull() }
        val first = parts.getOrNull(0) ?: 1
        val second = parts.getOrNull(1) ?: 0
        val patch = parts.getOrNull(2) ?: 0

        if (first >= 26) return 25

        return when {
            first == 1 && second >= 21 -> 21
            first == 1 && second == 20 && patch >= 5 -> 21
            first == 1 && second in 17..20 -> if (second == 17) 16 else 17
            first == 1 && second <= 16 -> 8
            else -> 8
        }
    }
}
