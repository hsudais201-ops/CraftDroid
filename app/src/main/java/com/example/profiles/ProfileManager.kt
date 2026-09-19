package com.example.profiles

import com.example.core.db.ProfileDao
import com.example.core.db.ProfileEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.firstOrNull

class ProfileManager(private val profileDao: ProfileDao) {

    val profiles: Flow<List<ProfileEntity>> = profileDao.getAllProfiles()

    suspend fun initDefaultProfilesIfNeeded() {
        val existing = profiles.firstOrNull()
        if (existing.isNullOrEmpty()) {
            profileDao.insertProfile(
                ProfileEntity(
                    name = "Vanilla Latest",
                    versionId = "1.21.4",
                    javaVersion = 21,
                    ramMb = 2048,
                    renderer = "Auto",
                    customJvmArgs = "",
                    modsEnabled = false
                )
            )
            profileDao.insertProfile(
                ProfileEntity(
                    name = "Modded 1.20.4",
                    versionId = "1.20.4",
                    javaVersion = 17,
                    ramMb = 3072,
                    renderer = "Auto",
                    customJvmArgs = "-XX:+UseG1GC",
                    modsEnabled = true
                )
            )
        }
    }

    suspend fun createProfile(
        name: String,
        versionId: String,
        javaVersion: Int,
        ramMb: Int,
        renderer: String,
        customJvmArgs: String,
        modsEnabled: Boolean
    ): Long {
        return profileDao.insertProfile(
            ProfileEntity(
                name = name,
                versionId = versionId,
                javaVersion = javaVersion,
                ramMb = ramMb,
                renderer = renderer,
                customJvmArgs = customJvmArgs,
                modsEnabled = modsEnabled
            )
        )
    }

    suspend fun duplicateProfile(profile: ProfileEntity): Long {
        return profileDao.insertProfile(
            profile.copy(id = 0, name = "${profile.name} (Copy)")
        )
    }

    suspend fun updateProfile(profile: ProfileEntity) {
        profileDao.updateProfile(profile)
    }

    suspend fun deleteProfile(id: Long) {
        profileDao.deleteProfileById(id)
    }
}
