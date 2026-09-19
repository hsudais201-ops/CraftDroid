# CraftDroid Launcher — Step 73

## Main fix: modern LWJGL3 uses the native GLFW backend

TeamPojavLauncher’s current `bhai-bhai` release replaced the old `lwjgl3glfw` Java stub with a real GLFW backend and changed its LWJGL packaging. CraftDroid was still forcing a Java GLFW stub for every Minecraft 1.13+ profile.

### Changes
- Modern Minecraft (1.13+) now selects `LWJGL3_NATIVE_GLFW`.
- Modern launches no longer download/inject `lwjgl-glfw-classes.jar` or the callback patch.
- The launch classpath prepends those compatibility jars only when legacy stub mode is explicitly used.
- `glfwstub.*` JVM properties are only emitted in legacy stub mode.
- Native stack loading recognizes `liblwjgl.so` and `liblwjgl3.so`.
- Native GLFW/LWJGL validation accepts either LWJGL native filename.
- Native LWJGL compatibility validation accepts either canonical filename.
- Embedded JLI launch path remains intact.
