# Step 144 — Input pump readiness invariant

- Native input pump now publishes `g_glfw_input_ready=false` whenever the pump thread exits.
- Prevents Java/native code from observing a stale ready state after an attach failure, unexpected thread exit, or requested shutdown.
- `g_input_requested` is intentionally preserved so Surface recreation can restore the pump when Minecraft is still running.
- JNI CallbackBridge global-reference cleanup remains after the readiness transition.
