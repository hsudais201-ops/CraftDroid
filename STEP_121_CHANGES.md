# Step 121 Changes

- Cache `org/lwjgl/glfw/CallbackBridge` as a JNI global reference from the embedded JVM callback thread.
- Cache `receiveCallback(IIIII)V` method ID at callback-bridge startup.
- Stop calling `FindClass()` from the native-created input thread; this avoids class-loader mismatch for the embedded Minecraft JVM.
- Preserve the existing VM/input readiness synchronization and event queue behavior.
