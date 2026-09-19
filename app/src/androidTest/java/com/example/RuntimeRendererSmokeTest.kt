package com.example

import android.content.Context
import android.os.Build
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.example.core.LauncherContainer
import com.example.renderer.RendererBackend
import com.example.renderer.RendererCompatibilityPolicy
import com.example.runtime.JavaRuntimeManager
import com.example.versions.MinecraftJavaVersionPolicy
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RuntimeRendererSmokeTest {

    @Test
    fun deviceArchitecture_andJavaPolicy_areConcrete() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val manager = LauncherContainer.get(context).javaManager
        val supported = Build.SUPPORTED_ABIS.map { it.lowercase() }

        assertTrue("Device must report an Android ABI", supported.isNotEmpty())
        val arch = manager.getArch()
        assertTrue("Runtime ABI mapping must match the device ABI", when (arch) {
            "arm64" -> supported.any { it.contains("arm64") || it.contains("aarch64") }
            "arm" -> supported.any { it.contains("armeabi") || it.contains("armv7") }
            "x86_64" -> supported.any { it == "x86_64" || it.contains("amd64") }
            "x86" -> supported.any { it == "x86" }
            else -> false
        })

        assertEquals(25, MinecraftJavaVersionPolicy.requiredMajor("26.1"))
        assertEquals(25, MinecraftJavaVersionPolicy.requiredMajor("26.3.1"))
        assertEquals(21, MinecraftJavaVersionPolicy.requiredMajor("1.21.11"))
        assertEquals(21, MinecraftJavaVersionPolicy.requiredMajor("1.20.6"))
        assertEquals(17, MinecraftJavaVersionPolicy.requiredMajor("1.20.4"))
        assertEquals(16, MinecraftJavaVersionPolicy.requiredMajor("1.17.1"))
        assertEquals(8, MinecraftJavaVersionPolicy.requiredMajor("1.16.5"))
    }

    @Test
    fun realJava21Runtime_downloads_extracts_and_starts() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val manager = LauncherContainer.get(context).javaManager

        val installed = kotlinx.coroutines.runBlocking {
            manager.installRuntime(21) {}
        }
        assertTrue("Java 21 Android runtime should install on the CI x86_64 emulator", installed)

        val smoke = kotlinx.coroutines.runBlocking { manager.testJava(21) }
        assertTrue("java -version must execute successfully", smoke.first)
        assertTrue("runtime version output should identify Java 21", smoke.second.contains("21"))
        val runtime = manager.runtimes.value.firstOrNull { it.majorVersion == 21 }
        assertNotNull(runtime)
        assertTrue(runtime!!.isValid)
    }

    @Test
    fun rendererProbe_andPolicy_are_real_device_data() {
        val context = ApplicationProvider.getApplicationContext<Context>()
        val container = LauncherContainer.get(context)
        val gpu = container.rendererManager.gpuInfo

        assertTrue(gpu.glEsVersion.isNotBlank())
        assertTrue(gpu.glRenderer.isNotBlank())
        assertTrue(gpu.glVendor.isNotBlank())

        val backend = container.rendererManager
        assertNotNull(gpu.recommendedBackend)

        val fakeVersion = com.example.versions.VersionDetail(
            id = "1.21.11",
            mainClass = "net.minecraft.client.main.Main",
            javaVersion = com.example.versions.JavaVersionInfo(majorVersion = 21),
            clientDownload = com.example.versions.VersionDownload("", 1L, "https://example.invalid/client.jar"),
            assetIndex = com.example.versions.AssetIndexInfo("1", "", 1L, 1L, "https://example.invalid/assets.json"),
            libraries = listOf(
                com.example.versions.Library("org.lwjgl:lwjgl:3.3.3", null),
            ),
            jvmArguments = emptyList(),
            gameArguments = emptyList()
        )
        val decision = RendererCompatibilityPolicy.choose(RendererBackend.AUTO, gpu, fakeVersion)
        assertTrue(decision.allowed)
    }
}
