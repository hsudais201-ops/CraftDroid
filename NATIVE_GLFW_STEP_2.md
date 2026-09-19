# CraftDroid — Step 2: Android Surface → GLFW → LWJGL → Minecraft

This step hardens the native hand-off instead of pretending that a set of `.so` files is enough.

## Runtime chain

```text
Android GameActivity / GameSurfaceView
        │ Surface
        ▼
ANativeWindow (CraftDroid JNI bridge)
        │
        ├── input queue → CallbackBridge → Android GLFW Java stub
        │
        └── global native symbols / renderer libraries
                    │
                    ▼
              GLFW / LWJGL native
                    │
                    ▼
             Minecraft Java main()
                    │
                    ▼
             OpenGL / renderer
                    │
                    ▼
          Android GPU / GameSurface
```

## Changes in this step

- Native stack loading remains dependency ordered and `RTLD_GLOBAL`.
- The launcher now validates the actual GLFW entry-point contract after loading the native stack.
- LWJGL is checked for a JNI entry point before Minecraft starts.
- Surface state is exposed through `CRAFTDROID_SURFACE_*` and `CRAFTDROID_GLFW_*` runtime variables.
- The GLFW Java stub is configured to initialize its EGL path (`glfwstub.initEgl=true`) instead of explicitly disabling it.
- The launch path still uses the Android GameSurface and embedded JLI JVM; no desktop GLFW window is created.

## Important limitation

A successful validation is not the same as a verified Minecraft boot. The exact native GLFW/LWJGL binaries must still be compatible with the selected Minecraft version and Android ABI, and the full stack must be tested on a real Android device. Current PojavLauncher sources explicitly build a dedicated `jre_lwjgl3glfw` GLFW stub and ship custom Android-native components, so CraftDroid must keep these pieces version-compatible.
