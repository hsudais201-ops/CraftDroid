# Step 146 Changes

- Added a native lifecycle guard to `craftdroid_glfw_shutdown()` so direct JNI/native shutdown calls cannot destroy EGL/GLFW resources while the embedded JVM is STARTING, RUNNING, or STOPPING.
- Removed a duplicate render-owner reset assignment in `nativeSetSurface()`.
- Preserved the existing EXITED/IDLE teardown behavior and Step 145 stale-input queue clearing.
