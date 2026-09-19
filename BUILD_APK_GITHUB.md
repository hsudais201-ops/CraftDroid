# Build CraftDroid APK with GitHub Actions

CraftDroid includes `.github/workflows/build-apk.yml` for an automated cloud build. The workflow is designed so GitHub Actions provides the Gradle installation, while the repository does not need to contain the Gradle wrapper JAR.

## Build it

1. Create a GitHub repository and upload the complete CraftDroid project.
2. Push the project to the `main` or `master` branch, or open **Actions → Build CraftDroid APK → Run workflow**.
3. Wait for the workflow to finish.
4. Open the completed run and download the `CraftDroid-debug-results-<run-number>` artifact.

## What CI does

- checks out the source;
- installs JDK 17;
- installs Gradle 9.6.0;
- installs Android SDK platform 36, Build Tools 36.0.0, NDK 27.2.12479018, and CMake 3.22.1;
- validates the Gradle configuration;
- runs JVM/unit tests;
- compiles Kotlin and the native JNI/GLFW bridge;
- builds `app-debug.apk`;
- checks the APK package name, launcher activity, and all four configured native ABIs;
- calculates a SHA-256 checksum;
- starts an Android API 35 x86_64 emulator, installs the APK, launches CraftDroid, and fails the workflow if the application process immediately dies;
- uploads the APK and diagnostics even when the emulator smoke test fails.

## Output

The APK is `app/build/outputs/apk/debug/app-debug.apk`. CI also produces `SHA256SUMS.txt`, `BUILD_MANIFEST.txt`, APK contents/badging diagnostics, and emulator logcat.

This is a debug APK for testing. The emulator smoke test verifies Android installation and launcher startup; it does **not** prove that a selected Minecraft version reaches the Minecraft title screen. Real Minecraft/JRE/LWJGL/renderer testing still requires a compatible device or emulator and installed game assets/runtime files.

## Automatic builds

Pushes to `main` or `master` rebuild when launcher source, Gradle configuration, wrapper files, or the workflow changes. Manual runs are always available through **workflow_dispatch**.
