# Step 85 — Strict LWJGL Validation Selection

- Native LWJGL validation now receives the same LWJGL-generation selection used by the loader.
- The native stack validator no longer probes/opens the alternate LWJGL JNI library.
- The GLFW handshake now validates the selected `liblwjgl3.so` for modern mode or `liblwjgl.so` for legacy mode.
- This prevents validation itself from accidentally loading an unwanted LWJGL JNI family after the loader has intentionally excluded it.
- Kotlin/JNI signatures were updated consistently.

Build note: the Gradle wrapper could not download Gradle because this environment cannot resolve `services.gradle.org`; static consistency checks passed.
