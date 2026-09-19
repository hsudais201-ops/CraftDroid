# Step 31 — Build Recovery / CI APK Build

The previous build failure was environmental: the container could not resolve `services.gradle.org`, so the Gradle Wrapper could not download Gradle 9.6.0. This is not an Android/Kotlin compiler error.

This step makes the repository's GitHub Actions build the authoritative APK build path. The workflow provisions JDK 17, Android SDK/NDK/CMake, and Gradle 9.6.0 on a GitHub-hosted runner, then runs unit tests and `:app:assembleDebug`, verifies the APK exists, and emits SHA-256.

Local/offline builds remain supported only when the required Gradle distribution and dependency artifacts are already cached. Gradle's `--offline` mode cannot download missing dependencies.
