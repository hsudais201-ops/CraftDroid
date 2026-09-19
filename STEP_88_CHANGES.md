# CraftDroid Step 88

- Native LWJGL validation now selects the exact JNI filename required by the resolved LWJGL API family.
- LaunchCommandBuilder now passes the selected Android GLFW library name to `org.lwjgl.glfw.libname`, so `libglfw3.so` maps to `glfw3` instead of always forcing `glfw`.
- Native GLFW API resolution no longer performs a fresh `dlopen` of an arbitrary GLFW variant; it observes only an already-loaded library with `RTLD_NOLOAD`.
- Native loader diagnostics retain the exact GLFW/LWJGL library names.
- Removed a dead duplicate LWJGL failure branch in native validation.
