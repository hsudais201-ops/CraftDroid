# Step 117 changes

- Made the GLFW input-pump startup report success/failure to its caller.
- `nativeSetInputReady()` now returns JNI_FALSE when the embedded JVM handle is unavailable or the pump thread cannot attach to the VM.
- Prevents a false READY state with no active input dispatcher.
- Added `<future>` and `<memory>` for the startup synchronization primitive.
