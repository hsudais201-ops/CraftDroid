package com.example

import android.content.Context
import androidx.test.core.app.ApplicationProvider
import com.example.downloader.HashVerifier
import com.example.filesystem.MinecraftFileSystem
import com.example.input.KeyboardManager
import com.example.launcher.LaunchCommandBuilder
import com.example.launcher.LaunchConfig
import com.example.logs.CrashAnalyzer
import com.example.versions.VersionJsonParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import java.io.File
import kotlinx.coroutines.runBlocking

@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34])
class LauncherCoreUnitTest {

    @Test
    fun testHashVerifier() {
        val tempFile = File.createTempFile("test_sha1", ".txt")
        try {
            tempFile.writeText("Minecraft Java Edition on Android")
            val hash = HashVerifier.computeSha1(tempFile)
            assertNotNull(hash)
            assertTrue(HashVerifier.verifySha1(tempFile, hash!!))
            assertFalse(HashVerifier.verifySha1(tempFile, "0000000000000000000000000000000000000000"))
        } finally {
            tempFile.delete()
        }
    }

    @Test
    fun testVersionJsonParserMinimal() {
        val sampleJson = """
            {
                "id": "1.21.4",
                "mainClass": "net.minecraft.client.main.Main",
                "minimumLauncherVersion": 21,
                "type": "release",
                "time": "2024-12-03T10:00:00+00:00",
                "releaseTime": "2024-12-03T10:00:00+00:00",
                "javaVersion": {
                    "component": "java-runtime-gamma",
                    "majorVersion": 21
                },
                "downloads": {
                    "client": {
                        "sha1": "abcdef123456",
                        "size": 30000000,
                        "url": "https://piston-data.mojang.com/v1/objects/test/client.jar"
                    }
                },
                "assetIndex": {
                    "id": "17",
                    "sha1": "112233",
                    "size": 50000,
                    "totalSize": 600000,
                    "url": "https://piston-meta.mojang.com/v1/packages/test/17.json"
                },
                "libraries": [
                    {
                        "name": "org.lwjgl:lwjgl:3.3.3",
                        "downloads": {
                            "artifact": {
                                "path": "org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar",
                                "sha1": "1122334455",
                                "size": 100000,
                                "url": "https://libraries.minecraft.net/org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar"
                            }
                        }
                    }
                ]
            }
        """.trimIndent()

        val parser = VersionJsonParser()
        val parsed = parser.parseVersionDetail(sampleJson)
        assertEquals("1.21.4", parsed.id)
        assertEquals("net.minecraft.client.main.Main", parsed.mainClass)
        assertEquals(21, parsed.javaVersion.majorVersion)
        assertNotNull(parsed.clientDownload)
        assertEquals(1, parsed.libraries.size)
        assertEquals("org/lwjgl/lwjgl/3.3.3/lwjgl-3.3.3.jar", parsed.libraries[0].artifact?.path)
    }

    @Test
    fun testKeyboardMapping() {
        val km = KeyboardManager()
        // Android KEYCODE_W (62) -> LWJGL Key W (87)
        assertEquals(87, km.mapAndroidKeyToMinecraft(android.view.KeyEvent.KEYCODE_W))
        // Android KEYCODE_SPACE (62) -> LWJGL Key Space (32)
        assertEquals(32, km.mapAndroidKeyToMinecraft(android.view.KeyEvent.KEYCODE_SPACE))
        // Android KEYCODE_ESCAPE (111) -> LWJGL Key Escape (256)
        assertEquals(256, km.mapAndroidKeyToMinecraft(android.view.KeyEvent.KEYCODE_ESCAPE))
    }

    @Test
    fun testCrashAnalyzer() {
        val oomLog = "Exception in thread \"main\" java.lang.OutOfMemoryError: Java heap space"
        val analysis = CrashAnalyzer.analyze(1, oomLog)
        assertTrue(analysis.summary.contains("Out of Memory"))
        assertTrue(analysis.recommendations.any { it.contains("RAM") })

        val javaMismatchLog = "java.lang.UnsupportedClassVersionError: net/minecraft/client/main/Main has been compiled by a more recent version of the Java Runtime"
        val javaAnalysis = CrashAnalyzer.analyze(1, javaMismatchLog)
        assertTrue(javaAnalysis.summary.contains("Java version incompatibility"))

        val linkLog = "java.lang.UnsatisfiedLinkError: liblwjgl.so: cannot open shared object file"
        val linkAnalysis = CrashAnalyzer.analyze(1, linkLog)
        assertTrue(linkAnalysis.summary.contains("Native library linkage"))
    }

    @Test
    fun testLaunchCommandBuilderArguments() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val fileSystem = MinecraftFileSystem(context)
        val parser = VersionJsonParser()
        val builder = LaunchCommandBuilder(fileSystem, parser)

        val sampleJson = """
            {
                "id": "1.21.4",
                "mainClass": "net.minecraft.client.main.Main",
                "javaVersion": { "majorVersion": 21 },
                "downloads": {
                    "client": { "sha1": "abc", "size": 100, "url": "http://dummy" }
                },
                "assetIndex": { "id": "17", "sha1": "abc", "size": 100, "totalSize": 100, "url": "http://dummy" },
                "libraries": []
            }
        """.trimIndent()

        val detail = parser.parseVersionDetail(sampleJson)
        val dummyJava = File(context.filesDir, "dummy_java")

        val config = LaunchConfig(
            versionDetail = detail,
            username = "Steve",
            uuid = "00000000-0000-0000-0000-000000000000",
            accessToken = "dummy_token",
            ramMb = 2048,
            customJvmArgs = "-XX:+UseG1GC",
            javaExecutable = dummyJava
        )

        val command = builder.buildCommand(config)
        assertEquals(dummyJava.absolutePath, command.executable)
        assertTrue(command.arguments.contains("-Xmx2048M"))
        assertTrue(command.arguments.contains("-XX:+UseG1GC"))
        assertTrue(command.arguments.contains("net.minecraft.client.main.Main"))
        assertTrue(command.arguments.contains("--username"))
        assertTrue(command.arguments.contains("Steve"))
        assertTrue(command.arguments.contains("--version"))
        assertTrue(command.arguments.contains("1.21.4"))
    }

    @Test
    fun testLocalTestProfileSecurityConstraints() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val container = com.example.core.LauncherContainer(context)
        val accountManager = container.accountManager
        val accountDao = container.database.accountDao()

        val testUuid = "test-uuid-12345"
        val testUsername = "DevTester"
        accountManager.createLocalTestProfile(testUsername, testUuid, "Dev")

        val account = accountDao.getAccountByUuid(testUuid)
        assertNotNull(account)
        assertTrue(account!!.isLocalTestProfile)
        assertEquals("Dev", account.avatarType)
        assertEquals(testUsername, account.username)

        // Security check: getValidAccessToken MUST return null and NEVER generate fake tokens or contact Microsoft
        val token = accountManager.getValidAccessToken(testUuid)
        assertNull(token)
    }

    @Test
    fun testTouchControlSystemAndInputMapping() = runBlocking {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val container = com.example.core.LauncherContainer(context)
        val touchManager = container.touchInputManager

        // 1. Verify Built-in Profiles Loaded
        val profiles = touchManager.allProfiles.value
        assertTrue(profiles.any { it.id == "default" })
        assertTrue(profiles.any { it.id == "pvp" })
        assertTrue(profiles.any { it.id == "survival" })
        assertTrue(profiles.any { it.id == "building" })
        assertTrue(profiles.any { it.id == "tablet" })
        assertTrue(profiles.any { it.id == "controller" })

        // 2. Test Control Duplication and Updating
        val layout = touchManager.currentLayout.value
        val jumpCtrl = layout.controls.first { it.action == com.example.input.ControlAction.JUMP }
        val originalCount = layout.controls.size

        touchManager.duplicateControl(jumpCtrl.id)
        val layoutAfterDup = touchManager.currentLayout.value
        assertEquals(originalCount + 1, layoutAfterDup.controls.size)

        val updatedJump = jumpCtrl.copy(sizeScale = 1.5f, opacity = 0.9f)
        touchManager.updateControl(updatedJump)
        val foundJump = touchManager.currentLayout.value.findControl(jumpCtrl.id)
        assertNotNull(foundJump)
        assertEquals(1.5f, foundJump!!.sizeScale)
        assertEquals(0.9f, foundJump.opacity)

        // 3. Test Multi-Touch Input Mapping to InputBridge
        val attackCtrl = layout.controls.first { it.action == com.example.input.ControlAction.ATTACK }
        // Pointer down on Attack -> Left Mouse Button DOWN
        touchManager.onControlPointerDown(attackCtrl, 101)
        assertTrue(touchManager.inputBridge.mouse.isButtonDown(0))
        assertTrue(touchManager.pressedControlIds.value.contains(attackCtrl.id))

        // Multi-touch: simultaneous Pointer down on Jump -> Space Key DOWN
        touchManager.onControlPointerDown(jumpCtrl, 102)
        assertTrue(touchManager.inputBridge.keyboard.isKeyDown(com.example.input.MinecraftKeyCodes.KEY_SPACE))
        assertTrue(touchManager.pressedControlIds.value.contains(jumpCtrl.id))

        // Pointer up on Attack -> Left Mouse Button UP, Jump still down
        touchManager.onControlPointerUp(101)
        assertFalse(touchManager.inputBridge.mouse.isButtonDown(0))
        assertTrue(touchManager.inputBridge.keyboard.isKeyDown(com.example.input.MinecraftKeyCodes.KEY_SPACE))

        // Pointer up on Jump
        touchManager.onControlPointerUp(102)
        assertFalse(touchManager.inputBridge.keyboard.isKeyDown(com.example.input.MinecraftKeyCodes.KEY_SPACE))

        // 4. Test Joystick WASD Mapping
        // Moving joystick up (deltaY < 0) -> W is down
        touchManager.onJoystickMove(0f, -40f, 60f, 0.15f)
        assertTrue(touchManager.inputBridge.keyboard.isKeyDown(com.example.input.MinecraftKeyCodes.KEY_W))

        // Release joystick -> W is released
        touchManager.onJoystickRelease()
        assertFalse(touchManager.inputBridge.keyboard.isKeyDown(com.example.input.MinecraftKeyCodes.KEY_W))

        // 5. Test Profile Export & Import
        val exportedJson = touchManager.exportActiveProfile()
        assertNotNull(exportedJson)
        assertTrue(exportedJson.contains("Default"))

        val importResult = touchManager.importProfile(exportedJson)
        assertTrue(importResult.isSuccess)
        val importedProfile = importResult.getOrNull()
        assertNotNull(importedProfile)
        assertTrue(importedProfile!!.isCustom)
    }

    @Test
    fun testSkinTextureGeneratorAndPresets() {
        // 1. Verify preset list contains all 10 skins
        val presets = com.example.skin.SkinPresets.presets
        assertEquals(10, presets.size)
        assertTrue(presets.any { it.id == "steve" })
        assertTrue(presets.any { it.id == "alex" })
        assertTrue(presets.any { it.id == "cyber_steve" })
        assertTrue(presets.any { it.id == "diamond_knight" })

        // 2. Generate preset bitmap for Steve
        val stevePreset = com.example.skin.SkinPresets.findById("steve")
        assertNotNull(stevePreset)
        val steveBitmap = com.example.skin.SkinTextureGenerator.generatePresetBitmap(stevePreset!!)
        assertEquals(64, steveBitmap.width)
        assertEquals(64, steveBitmap.height)
    }

    @Test
    fun testAccountProvidersAndValidation() {
        // 1. Test AccountProviderType enum
        assertEquals(com.example.auth.AccountProviderType.MICROSOFT, com.example.auth.AccountProviderType.fromId("MICROSOFT"))
        assertEquals(com.example.auth.AccountProviderType.ELY_BY, com.example.auth.AccountProviderType.fromId("ELY_BY"))
        assertEquals(com.example.auth.AccountProviderType.LOCAL_TEST, com.example.auth.AccountProviderType.fromId("LOCAL_TEST"))
        assertEquals(com.example.auth.AccountProviderType.MICROSOFT, com.example.auth.AccountProviderType.fromId("unknown"))

        assertTrue(com.example.auth.AccountProviderType.MICROSOFT.isOfficiallyAuthenticated)
        assertTrue(com.example.auth.AccountProviderType.ELY_BY.isOfficiallyAuthenticated)
        assertFalse(com.example.auth.AccountProviderType.LOCAL_TEST.isOfficiallyAuthenticated)

        // 2. Test ElyBy authorization URL generation
        val authUrl = com.example.auth.ElyByAccountProvider.buildAuthorizationUrl(
            clientId = "craftdroid_launcher_test",
            redirectUri = "http://localhost:8080/auth/callback"
        )
        assertTrue(authUrl.startsWith("https://account.ely.by/oauth2/v1"))
        assertTrue(authUrl.contains("client_id=craftdroid_launcher_test"))
        assertTrue(authUrl.contains("response_type=code"))
        assertTrue(authUrl.contains("scope=account_info+account_email"))

        // 3. Test Local Test Profile generation
        val localUuid = java.util.UUID.randomUUID().toString()
        val localAccount = com.example.core.db.AccountEntity(
            uuid = localUuid,
            username = "TestSteve",
            userHash = "",
            tokenExpiresAt = 0L,
            isSelected = true,
            isLocalTestProfile = true,
            providerType = com.example.auth.AccountProviderType.LOCAL_TEST.id,
            isAuthenticated = false,
            createdAt = System.currentTimeMillis()
        )
        assertEquals("LOCAL_TEST", localAccount.providerType)
        assertFalse(localAccount.isAuthenticated)
        assertTrue(localAccount.isLocalTestProfile)
    }
}
