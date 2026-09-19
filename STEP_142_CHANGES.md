# Step 142 Changes

- Hardened `CallbackBridge.nativeSetInputReady(true)` against lifecycle races.
- A callback dispatcher can now be enabled only while the embedded JVM is fully `RUNNING` (state 2).
- Late callbacks during JVM `STARTING` or `STOPPING` are rejected and cannot resurrect the input pump.
- Existing state-clearing behavior for a dead JVM remains intact.
