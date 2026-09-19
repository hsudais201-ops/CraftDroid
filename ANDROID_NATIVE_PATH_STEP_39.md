# CraftDroid Step 39 — Android Native Path Isolation

## Problem fixed

Minecraft version native archives are desktop-native artifacts. Putting their extracted `.so` files on Android's `java.library.path`, `org.lwjgl.librarypath`, or `LD_LIBRARY_PATH` can cause the JVM/LWJGL loader to select an incompatible desktop binary.

This can produce `UnsatisfiedLinkError`, missing glibc/libpthread dependencies, incompatible LWJGL Java/native versions, or native crashes.

## Changes

- `LaunchCommandBuilder` now exposes only the Android-compatible native stack through `java.library.path` and `org.lwjgl.librarypath`.
- Minecraft's extracted `natives/<version>` directory is retained for packaging/metadata but is no longer placed on the Android linker search path.
- `RendererManager` no longer adds the desktop Minecraft natives directory to `LD_LIBRARY_PATH`.
- The Android native stack remains first-class through `POJAV_NATIVEDIR`, renderer paths, and the native bridge.
- Fixed the LWJGL compatibility result variable scope in `MinecraftLaunchManager`.

## Why

PojavLauncher diagnostics show that incorrect native lookup paths and incompatible Java/native LWJGL versions can cause exactly these failures. Android also cannot satisfy desktop Linux dependencies such as `libpthread.so.0`. See the Pojav issue examples documented in the project research.

## Important limitation

This does not make arbitrary mod-provided native libraries Android-compatible. A mod that ships a desktop-only `.so` may still fail. Such failures must be handled by the launch diagnostics/repair layer rather than by putting all desktop natives into the global linker path.
