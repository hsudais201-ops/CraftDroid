# Step 135 Changes

- Fixed a real deadlock in `CallbackBridge.nativeSetInputReady(true)`: the code no longer holds `g_mutex` while `startInputPump()` joins/restarts the input thread.
- Input readiness is published only after the pump successfully starts; the existing pump-thread re-entrant path publishes readiness without self-joining.
- Failure still leaves the callback pipe disabled.
