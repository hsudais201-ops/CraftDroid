# CraftDroid Runtime Step 7 — Real shared EGL render path

This step removes the last major architectural error from the Step 4 preflight:
CraftDroid must not create a separate native `glfwCreateWindow()` context and then
expect Minecraft/LWJGL to render through another context.

The launcher now creates one Android `ANativeWindow`-backed EGL context and passes
its native handles to the Android Java GLFW stub using the properties documented by
the PojavLauncherTeam `lwjgl3-glfw-java` implementation:

- `glfwstub.initEgl=false`
- `glfwstub.eglDisplay`
- `glfwstub.eglContext`
- `glfwstub.eglSurfaceRead`
- `glfwstub.eglSurfaceDraw`
- `glfwstub.windowWidth`
- `glfwstub.windowHeight`

The embedded Minecraft JVM therefore has one intended render owner:

Android Surface -> CraftDroid EGL -> Java GLFW stub -> LWJGL -> Minecraft

The old native `glfwCreateWindow()` preflight is no longer used during launch.
This avoids a second context and makes the runtime compatible with the Android GLFW
stub model used by PojavLauncher.

## Verification status

This is an architecture/runtime change, not a real-device boot test. The project
still needs to be compiled and tested on an Android device with the exact GLFW stub,
LWJGL, JRE and renderer binaries for the selected ABI.
