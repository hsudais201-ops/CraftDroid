# GitHub Actions CI Preparation — Step 153

## Changes

- Hardened `.github/workflows/build-apk.yml` for cloud builds.
- CI installs Gradle 9.6.0 with `gradle/actions/setup-gradle@v6` and invokes that installed `gradle` executable directly.
- This avoids requiring `gradle/wrapper/gradle-wrapper.jar` inside the ZIP.
- Android SDK/NDK/CMake installation is explicit.
- Unit tests, Kotlin/native compilation, APK assembly, APK manifest/ABI checks, checksum generation, and an Android API 35 launcher smoke test are all part of the workflow.
- APK and diagnostics are uploaded with `if: always()` so failed emulator runs still leave logs available.

## Verification in this environment

- CI project structure checks: PASS.
- Workflow text/required-action checks: PASS.
- Local Gradle compilation: not completed because this environment cannot resolve `services.gradle.org`.
- Real Minecraft boot: not verified in this environment.
