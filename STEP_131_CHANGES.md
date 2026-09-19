# Step 131 Changes

- Reset the native GLFW render-owner thread whenever the Android surface/EGL context is replaced.
- Prevents a stale thread-affinity binding from rejecting the new Minecraft render thread after rotation/activity recreation.
- Keeps surface generation and existing input lifecycle behavior unchanged.
