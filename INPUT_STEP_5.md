# CraftDroid Runtime Step 5 — Embedded-JVM GLFW Input Pump

This step connects Android input events to the **embedded Minecraft JVM** instead of the Android/ART VM.

## What changed

- `CallbackBridge.nativeSetInputReady()` now captures the embedded JVM's `JavaVM*`.
- A native worker thread attaches to that JVM and periodically calls `glfwPollEvents()`.
- The same attached JVM thread drains CraftDroid's native Android input queue and invokes `CallbackBridge.receiveCallback(...)`.
- The pump stops cleanly before GLFW is destroyed.
- This avoids the previous architectural problem where an Android JNI `JNIEnv*` could be used to call classes belonging to the embedded Minecraft JVM.

## Input path

`GameSurfaceView` → `NativeGameBridge` → native event queue → embedded-JVM input pump → `CallbackBridge.receiveCallback()` → Android GLFW stub → Minecraft/LWJGL input APIs.

## Important limitation

The exact event-number ABI still depends on the installed Pojav/Amethyst GLFW stub version. This step does not claim a successful real-device Minecraft boot; that requires building and testing the APK with a matching native/runtime stack.
