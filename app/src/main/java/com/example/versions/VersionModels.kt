package com.example.versions

import org.json.JSONObject

data class VersionManifest(
    val latestRelease: String,
    val latestSnapshot: String,
    val versions: List<VersionSummary>
)

data class VersionSummary(
    val id: String,
    val type: String, // "release", "snapshot", "old_beta", "old_alpha"
    val url: String,
    val time: String,
    val releaseTime: String,
    val sha1: String,
    val isInstalled: Boolean = false,
    val javaRequirement: Int = 21
)

data class VersionDownload(
    val sha1: String,
    val size: Long,
    val url: String
)

data class AssetIndexInfo(
    val id: String,
    val sha1: String,
    val size: Long,
    val totalSize: Long,
    val url: String
)

data class LibraryArtifact(
    val path: String,
    val sha1: String,
    val size: Long,
    val url: String
)

data class LibraryRule(
    val action: String, // "allow" or "disallow"
    val osName: String? = null,
    val osVersion: String? = null,
    val osArch: String? = null
)

data class Library(
    val name: String,
    val artifact: LibraryArtifact?,
    val nativesClassifier: String? = null,
    val nativesArtifact: LibraryArtifact? = null,
    val rules: List<LibraryRule> = emptyList(),
    val extractExcludes: List<String> = emptyList()
)

data class JavaVersionInfo(
    val component: String = "java-runtime",
    val majorVersion: Int = 21
)

data class LoggingConfig(
    val clientFileId: String,
    val clientFilePath: String,
    val clientFileSha1: String? = null
)

data class VersionDetail(
    val id: String,
    val mainClass: String,
    val javaVersion: JavaVersionInfo,
    val clientDownload: VersionDownload,
    val assetIndex: AssetIndexInfo,
    val libraries: List<Library>,
    val jvmArguments: List<Any>, // String or JSONObject rule-based argument
    val gameArguments: List<Any>, // String or JSONObject rule-based argument
    val legacyMinecraftArguments: String? = null,
    val assets: String? = null,
    val logging: LoggingConfig? = null
)
