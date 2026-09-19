# Step 106

## Surface lifecycle safety

- Do not tear down EGL/GLFW or clear the Android native window while the embedded Minecraft JVM is still running.
- Surface destruction is deferred until the JVM stops, preventing native render threads from using destroyed handles.
- Added `flushDeferredSurfaceClear()` and invoked it after a confirmed JVM stop.
- Preserved an explicit `force` path for controlled teardown after the JVM is no longer running.
