# Step 107 Changes

- Flush deferred Android surface teardown immediately after the embedded JLI launch returns.
- This covers natural Minecraft exit and early native/JLI failure paths, not only an explicit Stop action.
- Prevents a destroyed `SurfaceView` from leaving stale EGL/GLFW resources pinned until a later manual lifecycle event.
- Cleanup remains gated by the native JVM-running check.
