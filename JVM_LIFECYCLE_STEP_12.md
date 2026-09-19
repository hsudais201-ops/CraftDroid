# CraftDroid Step 12 — Embedded JVM lifecycle

## Changes
- Treat Minecraft as an embedded JLI/HotSpot VM, not an Android `Process`.
- Track `JLI_Launch` with a native `g_java_running` flag.
- Add `NativeGameBridge.isJavaRunning()`.
- Add `NativeGameBridge.requestJavaStop()`.
- Stop requests locate the embedded JVM and call `java.lang.System.exit(0)`.
- Stop the native input pump after `JLI_Launch` returns.
- `MinecraftLaunchManager.kill()` now requests JVM shutdown, cleans GLFW state, and resets launcher state.

## Why
`runningProcess?.destroy()` could never stop Minecraft because `JLI_Launch` runs Minecraft inside CraftDroid's own process. Pojav-style launchers also use an embedded/native execution stack rather than treating Minecraft as a normal Android child process.

## Limitation
A hard native crash (SIGSEGV/SIGABRT) can still terminate the entire Android process. This step handles normal user-requested shutdown and Java-level exits; native crash isolation requires a separate process architecture.
