# CraftDroid Launcher — Step 70 Fixes

This revision starts the transition from the previous prototype/runtime-step project into a launchable Android Minecraft Java launcher.

## Fixed

1. **Kotlin compilation errors**
   - Fixed invalid `\\d` escapes in `RendererCompatibilityPolicy.kt`.
   - Fixed the invalid `"loaded \\d"` marker in `MinecraftLaunchManager.kt`.

2. **Application version**
   - Updated Android `versionName` from `2.3.0` to `2.4.0`.

3. **Pinned native upstream**
   - Removed the moving `releases/latest` Pojav URL.
   - The native bridge now targets the known `bhai-bhai` release, whose published changes include real GLFW, updated Mesa/EGL, and per-game LWJGL installation.

4. **Modern Pojav native-layout compatibility**
   - `pojavexec` is no longer treated as a mandatory filename. The current upstream release changed native architecture, so the hard gate now requires GLFW + LWJGL + a graphics backend.

5. **LWJGL matching**
   - Legacy LWJGL2 Minecraft now accepts a compatible Android LWJGL3 native family instead of requiring exactly 3.3.3.
   - LWJGL3 matching uses major/minor compatibility rather than rejecting every patch-level difference. The actual native JNI handshake remains a final launch gate.

6. **Optional renderer dependency**
   - MobileGlues is no longer downloaded on every first launch.
   - It is installed only when the downloaded native stack has no GL4ES, Zink/Mesa, or MobileGlues backend.

## Still requires real-device validation

The project cannot be honestly marked as fully working until the APK is built and installed on a physical Android/Chromebook device. The remaining validation target is:

`Minecraft files -> Android JRE -> JLI_Launch -> LWJGL -> GLFW -> EGL/renderer -> Android Surface -> title screen -> world -> input/audio`

The supplied environment cannot download Gradle 9.6 from `services.gradle.org`, so this revision was statically inspected but not compiled here.
