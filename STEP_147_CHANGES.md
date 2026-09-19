# Step 147 Changes

- Protected direct EGL teardown with the embedded-JVM lifecycle state machine.
- NativeGameBridge.nativeDestroyEgl() and the exported craftdroid_egl_destroy() now reject teardown during STARTING/RUNNING/STOPPING.
- Prevents late/direct EGL destruction from bypassing the existing GLFW lifecycle guard.
