# CraftDroid Step 40 — Reliable Gradle/CI APK Build

## Problem fixed

The previous workflow depended on the repository's custom `gradlew` bootstrap script and also ran Gradle wrapper validation even though the project does not contain `gradle/wrapper/gradle-wrapper.jar`. That could prevent the workflow from reaching the actual Android build.

## Fix

The GitHub Actions workflow now uses `gradle/actions/setup-gradle@v6` with an explicit Gradle `9.6.0` installation and invokes the `gradle` executable supplied by the action. This avoids requiring a wrapper JAR while still using the Gradle version required by AGP 9.4.0.

The emulator smoke test also launches the actual application ID `com.craftdroid.launcher` instead of the old `com.example.game` ID.

## Validation stages

1. JDK 17
2. Gradle 9.6.0
3. Android SDK 36 / Build Tools 36.0.0
4. NDK 27.2.12479018
5. CMake 3.22.1
6. Gradle configuration check
7. Unit tests
8. Kotlin + native compilation
9. Debug APK build
10. Four-ABI verification
11. Android emulator installation/startup test
12. APK artifact upload

## Important limitation

A successful Android smoke test proves that the CraftDroid APK installs and its launcher process starts. It does **not** prove that an arbitrary Minecraft version boots. Real Minecraft boot still requires a valid Minecraft installation, compatible JRE, libraries/assets, Android-native LWJGL/GLFW stack, renderer, and a valid authenticated session where required.
