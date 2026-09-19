# CraftDroid Step 55 — Minecraft startup detection

The embedded JVM runs in-process, so Android cannot use a child-process PID to decide whether Minecraft actually reached game initialization.

Step 55 adds a bounded log monitor while `JLI_Launch` is running. It looks for runtime markers that are emitted after the Java game reaches LWJGL/OpenGL initialization (`LWJGL Version`, `OpenGL version`, GLFW initialization) and later Minecraft initialization markers such as `Setting user:`, `OpenAL initialized`, and resource-manager/world messages.

These markers are diagnostic signals, not a claim that the title screen is visible. A full title-screen proof still requires an instrumented graphics/game-state check on a running device or emulator.
