# Native + Java GLFW adapter

CraftDroid 1.7 now contains the missing integration layer around the Pojav-style Android GLFW stub.

## What is included

1. `LwjglGlfwStubManager` downloads and validates `lwjgl-glfw-classes.jar` from the upstream Pojav project.
2. The stub is placed before Minecraft's normal LWJGL jars on the embedded JVM classpath.
3. `craftdroid-callback-bridge.jar` overrides the stub's `CallbackBridge` so it can load CraftDroid's JNI bridge from the same native directory.
4. `libcraftdroidbridge.so` implements the native methods expected by `CallbackBridge` and translates queued Android input into the Pojav callback event ABI.
5. `glfwstub.windowWidth`, `glfwstub.windowHeight`, and `glfwstub.initEgl=true` are supplied to the game JVM.

The Pojav project explicitly documents its `jre_lwjgl3glfw` build as the custom GLFW stub used for Minecraft 1.13+ on Android. CraftDroid follows that classpath strategy rather than trying to use desktop GLFW directly.

## Remaining device-specific work

The renderer libraries are still selected/downloaded separately. The exact EGL/GL backend behavior can vary by Android GPU and renderer (MobileGlues, GL4ES, or Zink). This project therefore should be tested on the target Chromebook/Android device with a known Minecraft version after the APK builds.
