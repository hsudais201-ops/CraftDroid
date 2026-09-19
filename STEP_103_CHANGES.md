# Step 103 changes

- Fixed MinecraftLaunchManager lifecycle cleanup for embedded JLI launches.
- `javaLaunchActive` is now cleared in a `finally` block for normal return, bridge failure, coroutine cancellation, and exceptions.
- Prevents `kill()` from treating a failed/cancelled launch as an active Minecraft JVM.
- Keeps launch-state recovery consistent after early native bridge failures.
