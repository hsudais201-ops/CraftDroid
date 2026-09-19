package com.example.core

import android.content.Context
import androidx.room.Room
import com.example.auth.AccountManager
import com.example.auth.ElyByAccountProvider
import com.example.auth.LocalTestProfileProvider
import com.example.auth.MicrosoftAccountProvider
import com.example.auth.MicrosoftAuthManager
import com.example.auth.MinecraftAuthManager
import com.example.auth.SecureAccountStorage
import com.example.core.db.AppDatabase
import com.example.downloader.DownloadManager
import com.example.filesystem.MinecraftFileSystem
import com.example.input.ControllerManager
import com.example.input.KeyboardManager
import com.example.input.TouchInputManager
import com.example.launcher.LaunchCommandBuilder
import com.example.launcher.MinecraftLaunchManager
import com.example.logs.LauncherLogger
import com.example.minecraft.MinecraftInstaller
import com.example.minecraft.ModManager
import com.example.minecraft.ModCompatibilityManager
import com.example.profiles.ProfileManager
import com.example.renderer.RendererManager
import com.example.runtime.JavaRuntimeManager
import com.example.settings.SettingsRepository
import com.example.versions.VersionJsonParser
import com.example.versions.VersionManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit

class LauncherContainer internal constructor(context: Context) {

    val context: Context = context.applicationContext

    companion object {
        @Volatile
        private var INSTANCE: LauncherContainer? = null

        fun get(context: Context): LauncherContainer {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: LauncherContainer(context.applicationContext).also { INSTANCE = it }
            }
        }
    }

    val appScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    val okHttpClient: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(60, TimeUnit.SECONDS)
            .writeTimeout(60, TimeUnit.SECONDS)
            .build()
    }

    val database: AppDatabase by lazy {
        Room.databaseBuilder(context, AppDatabase::class.java, "minecraft_launcher.db")
            .addMigrations(AppDatabase.MIGRATION_3_4)
            .fallbackToDestructiveMigration(dropAllTables = false)
            .build()
    }

    val fileSystem: MinecraftFileSystem by lazy { MinecraftFileSystem(context) }
    val secureStorage: SecureAccountStorage by lazy { SecureAccountStorage(context) }

    val msAuthManager: MicrosoftAuthManager by lazy { MicrosoftAuthManager(okHttpClient) }
    val mcAuthManager: MinecraftAuthManager by lazy { MinecraftAuthManager(okHttpClient) }

    val microsoftProvider: MicrosoftAccountProvider by lazy {
        MicrosoftAccountProvider(database.accountDao(), secureStorage, msAuthManager, mcAuthManager)
    }
    val elyByProvider: ElyByAccountProvider by lazy {
        ElyByAccountProvider(okHttpClient, database.accountDao(), secureStorage)
    }
    val localTestProvider: LocalTestProfileProvider by lazy {
        LocalTestProfileProvider(database.accountDao())
    }

    val accountManager: AccountManager by lazy {
        AccountManager(
            accountDao = database.accountDao(),
            secureStorage = secureStorage,
            microsoftProvider = microsoftProvider,
            elyByProvider = elyByProvider,
            localTestProvider = localTestProvider,
            msAuth = msAuthManager,
            mcAuth = mcAuthManager,
            appScope = appScope
        )
    }

    val downloadManager: DownloadManager by lazy { DownloadManager(okHttpClient) }
    val versionParser: VersionJsonParser by lazy { VersionJsonParser() }
    val versionInheritanceResolver: com.example.versions.VersionInheritanceResolver by lazy { com.example.versions.VersionInheritanceResolver(fileSystem, okHttpClient) }
    val installer: MinecraftInstaller by lazy {
        MinecraftInstaller(fileSystem, downloadManager, versionParser, database.installedVersionDao(), okHttpClient, versionInheritanceResolver)
    }
    val fabricLoaderInstaller: com.example.minecraft.FabricLoaderInstaller by lazy {
        com.example.minecraft.FabricLoaderInstaller(fileSystem, downloadManager, okHttpClient)
    }
    val forgeNeoForgeInstaller: com.example.minecraft.ForgeNeoForgeInstaller by lazy {
        com.example.minecraft.ForgeNeoForgeInstaller(fileSystem, downloadManager, okHttpClient, javaManager)
    }
    val quiltLoaderInstaller: com.example.minecraft.QuiltLoaderInstaller by lazy {
        com.example.minecraft.QuiltLoaderInstaller(fileSystem, downloadManager, okHttpClient)
    }

    val javaManager: JavaRuntimeManager by lazy { JavaRuntimeManager(fileSystem, okHttpClient) }

    val versionManager: VersionManager by lazy {
        VersionManager(fileSystem, installer, versionParser, database.installedVersionDao(), downloadManager, okHttpClient, javaManager)
    }
    val nativeComponentManager: com.example.renderer.NativeComponentManager by lazy { com.example.renderer.NativeComponentManager(context, fileSystem, okHttpClient) }
    val lwjglGlfwStubManager: com.example.renderer.LwjglGlfwStubManager by lazy { com.example.renderer.LwjglGlfwStubManager(context, fileSystem, okHttpClient) }
    val rendererManager: RendererManager by lazy { RendererManager(context, fileSystem, nativeComponentManager) }
    val settingsRepository: SettingsRepository by lazy { SettingsRepository(context) }
    val commandBuilder: LaunchCommandBuilder by lazy { LaunchCommandBuilder(fileSystem, versionParser) }

    val installationRepairManager: com.example.minecraft.InstallationRepairManager by lazy { com.example.minecraft.InstallationRepairManager(fileSystem, downloadManager) }

    val launchManager: MinecraftLaunchManager by lazy {
        MinecraftLaunchManager(fileSystem, accountManager, javaManager, rendererManager, commandBuilder, versionParser, settingsRepository, lwjglGlfwStubManager, versionInheritanceResolver, modCompatibilityManager, installationRepairManager, appScope)
    }

    val touchInputManager: TouchInputManager by lazy { TouchInputManager(context, appScope) }
    val keyboardManager: KeyboardManager by lazy { KeyboardManager() }
    val controllerManager: ControllerManager by lazy { ControllerManager() }
    val profileManager: ProfileManager by lazy { ProfileManager(database.profileDao()) }
    val modManager: ModManager by lazy { ModManager(fileSystem) }
    val modCompatibilityManager: ModCompatibilityManager by lazy { ModCompatibilityManager(fileSystem) }
    val skinManager: com.example.skin.SkinManager by lazy {
        com.example.skin.SkinManager(context, okHttpClient, fileSystem, database.accountDao())
    }

    init {
        LauncherLogger.init(context)
    }
}
