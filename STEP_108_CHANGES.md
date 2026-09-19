# Step 108 changes

- Deferred Android Surface replacement/resizing while the embedded Minecraft JVM is running.
- Applies the newest Surface only after JLI_Launch exits, preventing EGL/ANativeWindow destruction underneath LWJGL threads.
- Preserved explicit surface-destroy deferral and added one immediate native surface-update path for post-JVM flushing.
