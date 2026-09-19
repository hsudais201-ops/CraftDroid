# Step 90 Changes

- Fixed native GLFW lifecycle handle loss in `craftdroid_glfw_shutdown()`.
- The selected GLFW `dlopen` handle is now intentionally pinned for the life of the process instead of being nulled during bridge shutdown.
- GLFW function pointers are still cleared after termination and are re-resolved only from the same pinned handle on the next lifecycle.
- Prevents a later surface/render generation from probing and potentially binding a different GLFW ABI.
- No Gradle/APK build was claimed; environment dependency/network limitations remain unchanged.
