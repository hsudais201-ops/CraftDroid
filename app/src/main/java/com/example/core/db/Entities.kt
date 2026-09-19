package com.example.core.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "accounts")
data class AccountEntity(
    @PrimaryKey val uuid: String,
    val username: String,
    val userHash: String = "",
    val tokenExpiresAt: Long = 0L,
    val skinUrl: String? = null,
    val skinModel: String = "classic",
    val capeUrl: String? = null,
    val isSelected: Boolean = false,
    val isLocalTestProfile: Boolean = false,
    val providerType: String = if (isLocalTestProfile) "LOCAL_TEST" else "MICROSOFT",
    val isAuthenticated: Boolean = !isLocalTestProfile,
    val avatarType: String = "Default",
    val createdAt: Long = System.currentTimeMillis(),
    val lastUsedAt: Long = System.currentTimeMillis(),
    val addedAt: Long = System.currentTimeMillis()
) {
    val accountId: String get() = uuid
    val expiresAt: Long get() = tokenExpiresAt
}

@Entity(tableName = "profiles")
data class ProfileEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val versionId: String,
    val javaVersion: Int = 21,
    val ramMb: Int = 2048,
    val renderer: String = "Auto",
    val customJvmArgs: String = "",
    val modsEnabled: Boolean = false,
    val createdAt: Long = System.currentTimeMillis()
)

@Entity(tableName = "installed_versions")
data class InstalledVersionEntity(
    @PrimaryKey val versionId: String,
    val type: String, // release, snapshot
    val releaseTime: String,
    val javaRequirement: Int,
    val isCorrupted: Boolean = false,
    val installedAt: Long = System.currentTimeMillis()
)
