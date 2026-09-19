# CraftDroid Step 46 — Android ELF ABI Verification

This step hardens the native LWJGL/GLFW handoff by validating every bundled `.so`
against the current Android device ABI before the embedded JVM is started.

## What changed

- Added `NativeAbiVerifier`.
- Reads the ELF magic, ELF class (32/64-bit), endianness, and `e_machine` field.
- Supports `arm64-v8a`, `armeabi-v7a`, `x86_64`, and `x86`.
- Rejects invalid or wrong-architecture `.so` files before `dlopen()`/JVM startup.
- Native stack installation now validates ABI both before reuse and after download/extraction.
- LWJGL compatibility validation now includes an ELF ABI gate.

## Why this matters

A shared library can be present, have a plausible filename, and still be unusable
because it was built for a different CPU architecture or ELF class. On Android
that normally surfaces later as a native load/link failure. Step 46 moves that
failure earlier and reports the exact file and expected ABI.

## Verification status

Static source checks and ZIP integrity should be run after packaging. A real APK
build still depends on the project's external Gradle/Android toolchain being
available.
