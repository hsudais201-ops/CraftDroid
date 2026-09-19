# Step 125 changes

- Hardened GLFW input-pump startup failure cleanup.
- Threads that temporarily attach to the embedded JVM now detach on startup failure.
- A partially created CallbackBridge global JNI reference is released before reporting startup failure.
- Prevents JNI thread attachment leaks and stale callback references when input-pump startup cannot complete.
