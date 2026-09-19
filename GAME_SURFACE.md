# CraftDroid 1.6 — Embedded JVM + Android Surface bridge

CraftDroid 1.6 changes the critical architecture from `ProcessBuilder(java ...)` to an embedded Android OpenJDK launch path through `libjli.so` and `JLI_Launch`. This is required because a separately spawned Java process cannot directly share an `ANativeWindow` owned by the Android launcher process.

## Architecture

Android `GameSurfaceView`
→ `NativeGameBridge`
→ `craftdroidbridge`
→ `ANativeWindow` + native input queue
→ custom Android GLFW adapter
→ LWJGL GLFW calls
→ Minecraft Java VM

The JNI bridge exports:

- `craftdroid_get_native_window()`
- `craftdroid_get_surface_size()`
- `craftdroid_poll_native_event()`

The Java side starts the Android OpenJDK runtime with `lib/jli/libjli.so` and calls `JLI_Launch` in the same Android process.

## Important

The actual custom LWJGL GLFW implementation is not generated from scratch in this project. It must be built from the compatible open-source GLFW stub and linked/loaded alongside this bridge. Pojav's current build documentation likewise treats the GLFW stub as a separate build target (`:jre_lwjgl3glfw:build`).

CraftDroid therefore fails clearly rather than pretending that ordinary desktop LWJGL GLFW can render directly on an Android `Surface`.
