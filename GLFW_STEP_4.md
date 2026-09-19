# CraftDroid Step 4 — Native GLFW ↔ Android Surface

This step adds a native preflight for the real loaded GLFW library.

Flow:

Android Surface → ANativeWindow → CraftDroid JNI → native GLFW → GLFW window/context → EGL/OpenGL current context → Minecraft/LWJGL

The bridge dynamically resolves GLFW symbols and calls `glfwInit`, `glfwCreateWindow`, `glfwMakeContextCurrent`, and `glfwSwapBuffers`. It rejects a native library that only has the expected filenames but cannot create an Android-backed context.

This is a compatibility preflight, not a replacement for a genuine Android GLFW implementation. A desktop GLFW binary or incompatible Pojav/Amethyst build can still fail and must not be reported as supported.
