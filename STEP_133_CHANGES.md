# Step 133 Changes

- Prevent duplicate `SurfaceHolder` created/changed callbacks from causing repeated native EGL/GLFW recreation by deduplicating identical Surface + dimensions in `MinecraftLaunchManager`.
- Refactored `kill()` to run shutdown/grace-period work on the application IO dispatcher instead of blocking the Android UI thread.
- Added single-flight stop protection so repeated Stop/Back clicks cannot race native shutdown.
- Abort during pre-JVM launch now cancels the preparation coroutine; cancellation is handled separately from real launch failures so it returns to Idle instead of reporting an error.
- Reset-to-home now refuses to lie about an active embedded JVM and safely cancels only pre-JVM launch work.
