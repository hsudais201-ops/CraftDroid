package com.example.launcher

import org.junit.Test

/** Regression tests for final JVM/game argument validation. */
class LaunchArgumentsValidatorTest {
    @Test
    fun acceptsSingleManagedClasspathAndHeapArguments() {
        LaunchArgumentsValidator.validateJvmArguments(
            listOf("-Xms128m", "-Xmx768m", "-Djava.home=/data/java", "-Djava.library.path=/data/natives", "-cp", "a:b")
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsBothClasspathSpellings() {
        LaunchArgumentsValidator.validateJvmArguments(listOf("-cp", "a", "-classpath", "b"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsDuplicateManagedRuntimePathArguments() {
        LaunchArgumentsValidator.validateJvmArguments(
            listOf("-Djava.home=/a", "-Djava.home=/b")
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsDuplicateNativeLibraryPathArguments() {
        LaunchArgumentsValidator.validateJvmArguments(
            listOf("-Djava.library.path=/a", "-Djava.library.path=/b")
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsDuplicateLwjglLibraryPathArguments() {
        LaunchArgumentsValidator.validateJvmArguments(
            listOf("-Dorg.lwjgl.librarypath=/a", "-Dorg.lwjgl.librarypath=/b")
        )
    }

    @Test(expected = IllegalArgumentException::class)
    fun rejectsControlCharacters() {
        LaunchArgumentsValidator.validateJvmArguments(listOf("-Dname=bad\nvalue"))
    }
}
