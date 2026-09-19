# Step 55 — Minecraft startup detection

CraftDroid now watches the embedded JVM's stdout/stderr log while `JLI_Launch` is active. Because Minecraft runs inside the launcher process, this uses the existing `CRAFTDROID_LOG_FILE` rather than a child-process PID.

## Detected milestones

- JVM starting
- Minecraft main class started
- LWJGL initialized
- OpenGL renderer initialized
- Audio initialized
- Minecraft resources initialized
- Minecraft runtime initialized
- Startup failure
- JVM/Minecraft exited

The detector is intentionally diagnostic: it does not declare a successful boot solely from `JLI_Launch` returning. A non-zero exit code, crash report, HotSpot error log, or detected Java/native failure remains authoritative.
