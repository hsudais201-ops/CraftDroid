# Step 33 — Reproducible multi-ABI Android build

CraftDroid's CI build now uses the checked-in Gradle Wrapper rather than a separately installed Gradle version. The GitHub Actions runner provisions JDK 17, validates the wrapper, installs Android SDK 36, NDK 27.2.12479018 and CMake 3.22.1, then runs tests, Kotlin compilation, native compilation and `assembleDebug`.

The debug APK is configured to package the native bridge for:

- arm64-v8a
- armeabi-v7a
- x86_64
- x86

The workflow verifies that all four ABI directories are actually present in the APK before publishing it as an artifact. It also records a SHA-256 checksum and build manifest containing the source commit.

This is a CI/build-system improvement only. It does not prove that Minecraft itself boots on a physical Android device; that still requires device testing of the native LWJGL/GLFW/EGL stack.
