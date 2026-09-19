# CraftDroid Step 89

- Preserved the exact selected GLFW variant across native bridge shutdown/reinitialization.
- `resolveGlfwApiLocked()` now re-observes the previously selected `libglfw.so` or `libglfw3.so` instead of falling back to the first available variant.
- Native stack validation now rejects a GLFW selection/loaded-handle name mismatch.
- Java/native GLFW handshake now rejects a loaded GLFW binary whose exact filename differs from the launcher's selected binary.
- No new GLFW implementation is introduced by lifecycle re-resolution; `RTLD_NOLOAD` remains observational.
