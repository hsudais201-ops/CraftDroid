# Step 81 — Native GLFW launch-path cleanup

- Made `executeProcess` explicitly aware of whether a legacy GLFW stub is active.
- Legacy `glfwstub.*` EGL JVM properties are now injected only for a real legacy stub launch.
- Modern LWJGL3/native-GLFW launches no longer receive stale `glfwstub.*` EGL properties.
- `-Dglfwstub.debugInput=false` is now likewise limited to launches that actually include the stub JAR.
- Preserved the existing native Android EGL/surface environment variables for the modern backend.
