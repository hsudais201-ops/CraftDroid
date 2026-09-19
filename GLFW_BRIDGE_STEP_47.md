# CraftDroid Step 47 — GLFW Java/native bridge hardening

This step removes a lifecycle conflict in the native bridge.

## What changed

- The bridge no longer creates a second desktop-style `glfwCreateWindow()` for
  an Android Surface that is already owned by CraftDroid's EGL path.
- `craftdroid_glfw_prepare()` now validates the selected GLFW symbols and the
  existing shared EGL context instead.
- GLFW/EGL helper calls are bound to one owner thread and refuse cross-thread
  calls rather than silently switching OpenGL contexts.
- The selected GLFW `dlopen()` handle is kept pinned for the life of the
  process. This avoids unloading native code while the embedded Minecraft/LWJGL
  VM may still hold JNI/native function pointers.
- Shutdown clears the bridge's thread ownership state.

## Runtime contract

1. `GameActivity` supplies the Android `Surface`.
2. CraftDroid creates the shared EGL display/context/surface.
3. The launcher passes those handles to the Android GLFW Java stub.
4. The GLFW helper validates that shared context instead of creating another
   window.
5. Minecraft/LWJGL remains responsible for its Java-side GLFW calls.

The helper APIs are a preflight/synchronization layer; successful preflight is
not evidence that a particular Minecraft version has booted.
