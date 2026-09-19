# Step 58 — Minecraft render watchdog

Step 58 adds post-start render-stall diagnostics without treating every pause as a crash.

## Behavior
- Watches the native successful-frame counter only after the Minecraft render heartbeat has been observed.
- Records the last time a successful Android-surface frame swap was seen.
- If no new frame is observed for 8 seconds while the embedded JVM is active, emits a targeted renderer-stall diagnostic containing JVM state, surface generation, and frame count.
- The watchdog does **not** kill or restart Minecraft automatically; loading pauses and focus/surface transitions can be legitimate.
- The one-shot warning is cleared when a new frame is observed.

## Proof boundary
A watchdog warning means rendering stopped progressing for the configured interval. It does not by itself prove that the Minecraft process is permanently frozen.
