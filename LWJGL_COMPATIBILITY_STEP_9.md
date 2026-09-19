# CraftDroid Runtime Step 9 — LWJGL compatibility validation

Step 9 prevents a class of failures where valid-looking LWJGL jars from different release lines are mixed with the Android GLFW stub.

## Checks

- Requires `org.lwjgl:lwjgl` core for modern LWJGL3 versions.
- Collects every `org.lwjgl:*` version from the selected Minecraft version JSON.
- Rejects malformed Maven coordinates.
- Rejects mixed LWJGL release lines such as 3.2.x + 3.3.x.
- Validates the Android GLFW stub still contains `GLFW` and `CallbackBridge` contracts used by CraftDroid.
- Runs before the native stack is handed to the embedded JVM.

This is a compatibility gate, not a device boot guarantee. Native LWJGL/GLFW ABI compatibility still needs to be confirmed by loading the selected native libraries on an actual Android device.
