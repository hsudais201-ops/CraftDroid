# Step 140 changes

- Added a native guard in `nativeSetSurface()` so a late/duplicate Android Surface callback cannot destroy or replace EGL/GLFW resources while the embedded Minecraft JVM is running.
- Hardened `CallbackBridge.nativeSetInputReady(true)` to reject stale readiness requests when the embedded JVM is not running, preventing resurrection of the callback pump during JVM teardown.
- Kept existing Java-side Surface deferral and JVM-exit cleanup as the primary lifecycle path; the native guards provide the final race boundary.
