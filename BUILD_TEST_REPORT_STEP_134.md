# CraftDroid Step 134 — Build/Test Report

## Changes validated
- Duplicate `SurfaceHolder` created/changed callbacks are deduplicated by Surface identity + dimensions.
- Stop/abort work runs off the Android UI thread and is single-flight.
- Aborting before JVM startup cancels the preparation coroutine without converting cancellation into a launch error.
- Reset-to-home is prevented from falsely entering Idle while an embedded JVM is active.
- Relaunch surface readiness is seeded from an already-attached valid native Surface.
- Previous-iteration duplicate project/archive residue was removed from the source tree.

## Local checks
- LWJGL/GLFW handshake source verification: PASS
- JNI declaration/export parity: PASS (36 `NativeGameBridge` methods)
- Android XML parsing: PASS (10 XML files)
- Native C++ structural balance: PASS
- Gradle wrapper shell syntax: PASS
- Source artifact cleanliness: PASS
- ZIP integrity: PASS

## Build limitation
A full Gradle build and Android emulator run could not be executed in this environment. The project has no cached Gradle 9.6.0/Android SDK toolchain, and `services.gradle.org` cannot be resolved from this environment. Therefore this report does not claim an APK was built or that real Minecraft boot was verified.

## CI path
The repository contains `.github/workflows/build-apk.yml`, which builds the debug APK, runs unit tests, compiles Kotlin/native code, checks all four ABIs, and performs an Android emulator smoke test on a networked GitHub Actions runner.
