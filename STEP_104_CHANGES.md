# Step 104 changes

- Hardened Minecraft stop ordering in `MinecraftLaunchManager.kill()`.
- After requesting embedded JVM shutdown, the launcher waits briefly for `isJavaRunning()` to become false before tearing down GLFW/EGL resources.
- If the embedded VM does not stop within the grace period, GLFW/EGL teardown is intentionally skipped to avoid destroying native graphics state while Minecraft/LWJGL threads may still access it.
- This prevents a Stop action from causing native use-after-free crashes in the Android Surface/GLFW bridge.
- Existing process cleanup and launch-state reset remain intact.
