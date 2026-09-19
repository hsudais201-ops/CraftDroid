# CraftDroid Step 8 — GLFW Stub Compatibility

This step makes the Android GLFW compatibility layer prefer the maintained
PojavLauncher-shipped stub instead of the archived standalone
`lwjgl3-glfw-java` artifact.

## Changes

- Prefer the GLFW stub bundled in the current PojavLauncher source tree.
- Keep the older `v3_openjdk` asset as a fallback.
- Keep the archived standalone stub only as a last-resort fallback.
- Validate that the JAR contains `GLFW.class` and `CallbackBridge.class`.
- Validate bytecode symbols used by CraftDroid's native callback bridge:
  `receiveCallback`, `nativeSendData`, `nativeSetInputReady`,
  `nativeClipboard`, and `nativeSetGrabbing`.
- Validate the GLFW class contains the expected `glfwInit` and
  `glfwPollEvents` API symbols.

## Why

PojavLauncher documents `jre_lwjgl3glfw` as a dedicated build component and
its repository notes that the old standalone `lwjgl3-glfw-java` repository is
archived. The launcher build produces the GLFW stub as part of the main source
tree. CraftDroid should therefore use the same maintained artifact whenever
possible.

This step does not claim device boot success. The next validation still needs
a real Minecraft version, matching LWJGL libraries, native binaries, and a
real Android device/emulator.
