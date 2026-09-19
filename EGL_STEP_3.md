# CraftDroid Step 3 — Android Surface → EGL → OpenGL → Minecraft

This step makes the Android `Surface` usable as a real EGL window surface from the same native process that launches Minecraft through `libjli`.

## Implemented

- `ANativeWindow` is retained from the Android `Surface`.
- Native EGL display/config/context/surface are created from that window.
- EGL ES 3 is preferred; ES 2 is used as a fallback.
- The EGL context is made current on the Minecraft/JLI launch thread.
- Renderer/vendor/version diagnostics are captured through `glGetString`.
- `eglSwapBuffers()` is exposed to an Android GLFW implementation.
- Surface destruction tears down EGL before releasing the native window.
- The launch environment advertises the EGL bridge to the native stack.

## Important limitation

This is the EGL foundation/bridge, not a guarantee that an arbitrary downloaded GLFW `.so` will call these functions. A compatible Android GLFW implementation must connect its `glfwCreateWindow`, `glfwMakeContextCurrent`, and `glfwSwapBuffers` operations to this bridge (or provide an equivalent EGL implementation).

The next verification target is therefore **GLFW window creation + LWJGL OpenGL context creation + first Minecraft frame + swap buffers** on a real Android device.
