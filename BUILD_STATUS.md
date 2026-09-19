# CraftDroid 2.4 Fixed — completion update

This revision fills several code-level gaps identified during inspection:

- Native libraries are loaded with `RTLD_GLOBAL` in dependency order so JNI/native symbol resolution is more reliable.
- Embedded JVM stdout/stderr can now be captured to `.minecraft/logs/craftdroid-jvm.log`.
- Crash analysis reads the captured JVM log instead of an always-empty buffer.
- Touch input now tracks the real screen cursor position and handles secondary pointers without generating duplicate mouse clicks.
- Android gamepad buttons are routed through the native input bridge.
- Gamepad axes are forwarded through the GLFW callback bridge instead of being discarded.
- The existing Android Surface API remains the shared rendering/input surface.

## Important limitation

This project still does **not** contain a complete Android Minecraft runtime. It obtains native runtime components and Java runtimes externally. A successful build therefore does not prove that Minecraft will boot on a device.

The final runtime chain still needs a compatible Android JRE/JLI, Minecraft LWJGL/native libraries, GLFW backend, graphics translation layer, and audio/native components for the target ABI. These components must be tested together on the actual device.

Do not describe this ZIP as a guaranteed working Minecraft launcher until a real device successfully launches a vanilla Minecraft version and reaches the title screen.
