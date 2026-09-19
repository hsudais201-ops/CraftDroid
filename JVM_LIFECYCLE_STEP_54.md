# Step 54 — Embedded JVM lifecycle hardening

CraftDroid now tracks the embedded JLI/JVM bridge with explicit native states:

- 0 IDLE
- 1 STARTING
- 2 RUNNING (inside `JLI_Launch`)
- 3 STOPPING
- 4 EXITED

A second concurrent `JLI_Launch` is rejected. Stop requests mark the bridge as STOPPING before asking the embedded Java VM to exit. The launcher logs the bridge state around startup and shutdown so a JLI failure, clean exit, and active embedded VM are not conflated.

This layer still does not claim that `RUNNING` means Minecraft reached the title screen: it means the embedded JLI call is active. Real Minecraft initialization remains a later verification stage.
