# Step 32 — Reliable Android APK Build Pipeline

CraftDroid now has a network-enabled CI build path intended to produce a real APK on GitHub Actions rather than depending on the restricted local build environment.

## Pipeline

1. Checks out the source.
2. Installs JDK 17.
3. Provisions Gradle 9.6.0 with the official `gradle/actions/setup-gradle@v6` action.
4. Installs Android SDK platform/build-tools, NDK 27.2.12479018 and CMake 3.22.1.
5. Validates the toolchain and Gradle configuration.
6. Runs unit tests.
7. Compiles Kotlin and the external native CMake build.
8. Builds `app-debug.apk`.
9. Verifies the APK is non-empty and records its SHA-256.
10. Uploads the APK and checksum as a GitHub Actions artifact.

## Wrapper hardening

`gradle/wrapper/gradle-wrapper.properties` pins Gradle 9.6.0 and its official SHA-256 checksum. The repository's lightweight `gradlew` bootstrap now verifies that checksum after download and retries transient network failures.

The official Gradle checksum for the 9.6.0 binary distribution is `bbaeb2fef8710818cf0e261201dab964c572f92b942812df0c3620d62a529a01`.

## Important

The CI workflow is configured to perform the real build, but this restricted environment still cannot execute that networked GitHub Actions runner. A successful APK build should only be reported after the workflow itself reaches the `Build CraftDroid debug APK` and `Verify APK` steps successfully.
