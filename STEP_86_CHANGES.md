# CraftDroid Step 86

## Native GLFW selection hardening

- Selects exactly one supported GLFW filename (`libglfw.so` or `libglfw3.so`) before the RTLD_GLOBAL dependency scan.
- Removes the alternate GLFW filename before generic dependency loading.
- Native stack validation now validates the GLFW handle already selected by the loader instead of dlopening a candidate and potentially introducing a second GLFW ABI.
- GLFW fallback during validation uses `RTLD_NOLOAD` only.
- Selected LWJGL validation is also observation-only (`RTLD_NOLOAD`) so validation cannot introduce an unselected JNI library.
- Updated JNI/Kotlin signature consistently.
