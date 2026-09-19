# Step 37 — JVM/Class/Native Failure Prevention

CraftDroid now performs a classpath preflight before starting the embedded JVM and classifies post-launch failures.

## Prevented before startup
- Missing/empty classpath JARs
- Missing Minecraft main class
- Invalid classpath entries
- Basic duplicate-main-class warning

## Classified after startup
- ClassNotFoundException / NoClassDefFoundError
- UnsatisfiedLinkError / dlopen failures
- SIGSEGV / SIGABRT / HotSpot fatal errors
- Java class-version mismatch
- OutOfMemoryError / Android process kills
- GLFW/EGL/OpenGL failures
- Fabric/Forge loader failures

Native crashes cannot be caught as ordinary Kotlin exceptions because the native process/JVM can terminate abruptly. CraftDroid therefore relies on HotSpot `hs_err_pid*.log`, logcat, and the native diagnostics bundle to identify them, while refusing to continue when preflight detects an invalid classpath.
