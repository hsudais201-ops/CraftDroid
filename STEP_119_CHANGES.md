# Step 119 Changes

- Clear pending native input events when the GLFW callback/input bridge is shut down.
- Prevent stale mouse, key, gamepad, scroll, and character events from a previous Minecraft JVM from being delivered to a later session.
- Keep normal surface replacement behavior unchanged: surface changes do not discard the live input queue.
- Count discarded queued events as dropped input for diagnostics.
