# CraftDroid Step 48 — LWJGL Java/native handshake

## Goal
Verify the final LWJGL/GLFW boundary immediately before JLI starts Minecraft.

## Changes
- Added a JNI handshake that checks the loaded Android GLFW binary for the required entry points.
- Checks for `JNI_OnLoad` in the loaded Android `liblwjgl.so`.
- Checks the four `CallbackBridge` JNI exports used by the Android input/clipboard/grab path.
- The handshake is deliberately non-invasive: it does not create a window or bind GLFW ownership to the launcher thread.
- Minecraft launch now stops before JLI when the ABI contract is incomplete.

## Why this matters
A native library can exist and even pass an ABI check while still being the wrong API build. This catches missing GLFW symbols, missing LWJGL JNI initialization, and stale callback-patch/native mismatches before the embedded JVM reaches Minecraft rendering initialization.

## Verification
- Kotlin/native source references checked for matching JNI method names.
- C++ handshake added without changing existing EGL ownership.
- ZIP integrity verified for the Step 48 package.

## Limitation
This validates the library/API boundary; it does not prove a particular Minecraft version will fully boot. Full boot still requires a compatible Java runtime, complete Mojang libraries/assets, session state, renderer support, and device-side execution.
