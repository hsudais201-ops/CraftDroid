# CraftDroid Android GLFW/LWJGL bridge

CraftDroid 1.7 now installs the Pojav-style Android GLFW Java stub at first launch.

The stub is placed in `.minecraft/lwjgl3/lwjgl-glfw-classes.jar` and is inserted **before** the normal Minecraft LWJGL libraries on the embedded JVM classpath. This is important because Pojav's Android GLFW layer is a Java stub rather than a normal desktop GLFW implementation.

At runtime CraftDroid also exposes the native JNI methods expected by `org.lwjgl.glfw.CallbackBridge`:

- `nativeSendData`
- `nativeSetInputReady`
- `nativeClipboard`
- `nativeSetGrabbing`

Android touch, keyboard and controller events are queued by `libcraftdroidbridge.so` and forwarded to `CallbackBridge.receiveCallback(...)` when the GLFW stub enables input.

The launcher sets:

- `glfwstub.windowWidth`
- `glfwstub.windowHeight`
- `glfwstub.initEgl=true`

The Android `SurfaceView` is still the authoritative game surface. The remaining renderer-specific EGL behavior depends on the exact Pojav/MobileGlues/GL4ES native component selected on the device.

## Upstream reference

The PojavLauncher project documents building its custom `jre_lwjgl3glfw` module and describes Minecraft 1.13+ support through a GLFW stub. See the project README and the older `lwjgl3-glfw-java` project for the design reference.
