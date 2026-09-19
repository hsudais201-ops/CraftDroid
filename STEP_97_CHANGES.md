# Step 97 Changes

- Fixed embedded JVM relaunch state handling.
- `nativeLaunchJava` now accepts both `IDLE` and `EXITED` as valid starting states.
- Preserves `EXITED` for diagnostics after Minecraft returns while allowing the next launch to transition back to `STARTING`.
- Rejects overlapping `STARTING`, `RUNNING`, and `STOPPING` launches as before.
