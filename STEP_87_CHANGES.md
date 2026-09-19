# Step 87 — Native GLFW/LWJGL Handle Integrity

- Tracked the exact LWJGL JNI handle selected by `NativeGameBridge.loadNativeStack()`.
- GLFW/LWJGL handshake validation now observes already-loaded handles instead of opening missing/alternate libraries.
- GLFW handshake receives the exact selected filename (`libglfw.so` or `libglfw3.so`).
- Removed the remaining validation path that could load a second LWJGL implementation with `dlopen()`.
- Native handles are cleared with the bridge shutdown state so a later stack load can establish fresh handles.
- Kotlin JNI signature and launch-manager call were updated consistently.
- No APK/real Minecraft boot claim: the environment still cannot resolve the Gradle distribution/dependencies needed for a full Android build.
