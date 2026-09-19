# CraftDroid Step 56 — Render-loop proof

Adds a native render-loop heartbeat to distinguish Minecraft Java startup from a successful frame presented through the CraftDroid Android-surface bridge.

- `craftdroid_glfw_swap_buffers()` increments an atomic frame counter only after `eglSwapBuffers()` succeeds.
- JNI exposes the successful-frame count and the last successful frame timestamp.
- The Minecraft startup monitor samples the counter while the embedded JVM is running.
- A heartbeat log is emitted only after the counter increases, avoiding false proof from the pre-launch GLES test.

This is intentionally stronger than log-marker detection, but it still does not claim title-screen visibility or successful world loading.
