# Step 92 Changes

- Made the recorded native GLFW ABI identity process-stable; a later load cannot switch between `libglfw.so` and `libglfw3.so`.
- Made the recorded LWJGL JNI ABI identity process-stable; a later load cannot switch between `liblwjgl.so` and `liblwjgl3.so`.
- A conflicting ABI load now fails instead of silently replacing the active bridge identity.
- Preserved existing exact-name selection and handle-based validation.
