# Step 105 — Embedded JVM concurrent-launch guard

- Prevented `MinecraftLaunchManager.launch()` from cancelling/replacing an existing launch job while the embedded JVM is active.
- Concurrent launch attempts now fail cleanly with a user-facing `LaunchState.Error`.
- This avoids racing the synchronous `JLI_Launch()` native call and corrupting JVM/GLFW/EGL lifecycle state.
