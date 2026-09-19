# CraftDroid Step 50 — OpenGL/LWJGL Rendering Bootstrap

Step 50 adds a native OpenGL ES capability gate immediately after the real Android EGL frame test and before the embedded Minecraft JVM starts.

## What changed

- `NativeGameBridge.validateOpenGlBootstrap()` now queries the live Android EGL context for:
  - `GL_VERSION`
  - `GL_VENDOR`
  - `GL_RENDERER`
  - maximum 2D texture size
  - texture image units
  - maximum viewport dimensions
  - framebuffer-related extension presence
  - floating-point texture extension presence
- `MinecraftLaunchManager` refuses to start Minecraft when the GLES capability query fails.
- The launcher exports `CRAFTDROID_GL_BOOTSTRAP=1` so downstream renderer/native diagnostics can identify that the capability gate passed.
- No second EGL context or desktop GLFW window is created by this step.

## Why this matters

A successful `eglMakeCurrent`/buffer swap only proves that the Android surface can render a basic frame. LWJGL/Minecraft immediately performs additional OpenGL capability queries and creates resources such as textures, framebuffers, and viewports. Step 50 validates those capabilities while the same EGL context is active.

## Verification status

This source package contains the new native/JNI contract and launch gate. The local environment still lacks a usable Gradle distribution/network path, so an Android APK build cannot be truthfully marked as completed here.
