package com.example.core.db

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.RoomDatabase
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface AccountDao {
    @Query("SELECT * FROM accounts ORDER BY addedAt DESC")
    fun getAllAccounts(): Flow<List<AccountEntity>>

    @Query("SELECT * FROM accounts WHERE isSelected = 1 LIMIT 1")
    fun getSelectedAccountFlow(): Flow<AccountEntity?>

    @Query("SELECT * FROM accounts WHERE isSelected = 1 LIMIT 1")
    suspend fun getSelectedAccount(): AccountEntity?

    @Query("SELECT * FROM accounts WHERE uuid = :uuid LIMIT 1")
    suspend fun getAccountByUuid(uuid: String): AccountEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAccount(account: AccountEntity)

    @Query("UPDATE accounts SET isSelected = 0")
    suspend fun clearSelected()

    @Query("UPDATE accounts SET isSelected = 1 WHERE uuid = :uuid")
    suspend fun setSelected(uuid: String)

    @Query("UPDATE accounts SET skinUrl = :skinUrl, skinModel = :skinModel WHERE uuid = :uuid")
    suspend fun updateSkin(uuid: String, skinUrl: String?, skinModel: String)

    @Query("UPDATE accounts SET lastUsedAt = :timestamp WHERE uuid = :uuid")
    suspend fun updateLastUsed(uuid: String, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE accounts SET username = :username, lastUsedAt = :timestamp WHERE uuid = :uuid")
    suspend fun updateUsername(uuid: String, username: String, timestamp: Long = System.currentTimeMillis())

    @Delete
    suspend fun deleteAccount(account: AccountEntity)

    @Query("DELETE FROM accounts WHERE uuid = :uuid")
    suspend fun deleteAccountByUuid(uuid: String)
}

@Dao
interface ProfileDao {
    @Query("SELECT * FROM profiles ORDER BY id ASC")
    fun getAllProfiles(): Flow<List<ProfileEntity>>

    @Query("SELECT * FROM profiles WHERE id = :id LIMIT 1")
    suspend fun getProfileById(id: Long): ProfileEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProfile(profile: ProfileEntity): Long

    @Update
    suspend fun updateProfile(profile: ProfileEntity)

    @Delete
    suspend fun deleteProfile(profile: ProfileEntity)

    @Query("DELETE FROM profiles WHERE id = :id")
    suspend fun deleteProfileById(id: Long)
}

@Dao
interface InstalledVersionDao {
    @Query("SELECT * FROM installed_versions ORDER BY installedAt DESC")
    fun getAllInstalledVersions(): Flow<List<InstalledVersionEntity>>

    @Query("SELECT * FROM installed_versions WHERE versionId = :versionId LIMIT 1")
    suspend fun getInstalledVersion(versionId: String): InstalledVersionEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertInstalledVersion(version: InstalledVersionEntity)

    @Query("DELETE FROM installed_versions WHERE versionId = :versionId")
    suspend fun deleteInstalledVersion(versionId: String)
}

@Database(
    entities = [AccountEntity::class, ProfileEntity::class, InstalledVersionEntity::class],
    version = 4,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun accountDao(): AccountDao
    abstract fun profileDao(): ProfileDao
    abstract fun installedVersionDao(): InstalledVersionDao

    companion object {
        val MIGRATION_3_4 = object : androidx.room.migration.Migration(3, 4) {
            override fun migrate(db: androidx.sqlite.db.SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE accounts ADD COLUMN capeUrl TEXT")
                db.execSQL("ALTER TABLE accounts ADD COLUMN providerType TEXT NOT NULL DEFAULT 'MICROSOFT'")
                db.execSQL("ALTER TABLE accounts ADD COLUMN isAuthenticated INTEGER NOT NULL DEFAULT 1")
                db.execSQL("ALTER TABLE accounts ADD COLUMN createdAt INTEGER NOT NULL DEFAULT 0")
                db.execSQL("ALTER TABLE accounts ADD COLUMN lastUsedAt INTEGER NOT NULL DEFAULT 0")
                db.execSQL("UPDATE accounts SET providerType = 'LOCAL_TEST', isAuthenticated = 0 WHERE isLocalTestProfile = 1")
            }
        }
    }
}
