# Step 82 changes

- Native LWJGL loading is now API-family aware.
- Modern `LWJGL3_NATIVE_GLFW` launches select `liblwjgl3.so` and skip an alternate `liblwjgl.so` when both are bundled.
- Legacy LWJGL2-compatible launches select `liblwjgl.so` and skip an alternate `liblwjgl3.so`.
- This prevents global JNI/symbol resolution from depending on native-library directory ordering.
- Existing GLFW, renderer, and dependency validation remain the final gates.
