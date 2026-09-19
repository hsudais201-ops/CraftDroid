# Step 113 changes

- Fixed duplicate Android Surface lifecycle dispatch in `GameActivity`.
- `GameActivity` no longer calls `NativeGameBridge.setSurface()` directly before `MinecraftLaunchManager.onGameSurfaceReady()`.
- `GameActivity` no longer calls `NativeGameBridge.clearSurface()` directly before `MinecraftLaunchManager.onGameSurfaceDestroyed()`.
- This prevents double native surface replacement/teardown, duplicate EGL/GLFW recreation, and incorrect surface-generation increments.
