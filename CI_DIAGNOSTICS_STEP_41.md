# CraftDroid Step 41 — Build Artifact and Emulator Diagnostics

This step hardens the CI pipeline after the Gradle execution fix.

## Changes

1. **APK package verification**
   - Confirms the generated APK exists and is non-empty.
   - Uses `aapt2 dump badging` to verify the real application ID:
     `com.craftdroid.launcher`.
   - Verifies the launcher activity is `com.example.MainActivity`.

2. **Native ABI verification**
   - Requires `arm64-v8a`, `armeabi-v7a`, `x86_64`, and `x86`.
   - Explicitly requires `libcraftdroidbridge.so` for every ABI.
   - This catches the common case where the APK builds but the JNI bridge is absent for the device architecture.

3. **Failure diagnostics**
   - APK listing and `aapt2` manifest output are preserved.
   - Emulator logcat is preserved when available.
   - The artifact upload now uses `if: always()` so build/emulator failures do not discard diagnostics.

4. **No false success claim**
   - A successful launcher smoke test proves that the Android application can install and start.
   - It does **not** prove that a Minecraft version has successfully booted through Java + LWJGL + GLFW + renderer + assets. Real Minecraft boot remains a separate runtime test.

## Why this matters

The project previously had several layers where a failure could be hidden: Gradle setup, APK packaging, ABI packaging, Android manifest identity, launcher process startup, and native/JNI loading. Step 41 makes the first five observable in one CI artifact.
