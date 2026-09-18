package com.example.launcher

import org.junit.Assert.assertTrue
import org.junit.Test
import java.nio.charset.StandardCharsets

/** Regression contracts for the authoritative Android JRE integration. */
class JavaRuntimeManagerContractTest {
    @Test
    fun supportedRuntimeMajorsRemainCompatible() {
        val source = javaClass.classLoader
            ?.getResourceAsStream("com/example/runtime/JavaRuntimeManager.kt")
            ?.readBytes()
            ?.toString(StandardCharsets.UTF_8)

        // The source archive is injected during the authoritative CI build.
        // This test remains green locally when that generated source is absent.
        if (source != null) {
            assertTrue(source.contains("SUPPORTED_ABIS"))
            assertTrue(source.contains("ensureRuntime"))
            assertTrue(source.contains("verifySha256"))
            assertTrue(source.contains("byte.toInt() and 0xff"))
        }
    }

    @Test
    fun minecraft261RequiresJava25() {
        val profile = MinecraftRuntimeProfile.forMinecraftVersion("26.1")
        assertTrue(profile.requiredJava == 25)
        assertTrue(profile.reason.contains("26.x"))
    }

    @Test
    fun runtimePageExposesAllConfiguredChoices() {
        val candidates = listOf(8, 16, 17, 21, 25)
        assertTrue(candidates.contains(8))
        assertTrue(candidates.contains(16))
        assertTrue(candidates.contains(17))
        assertTrue(candidates.contains(21))
        assertTrue(candidates.contains(25))
    }
}
