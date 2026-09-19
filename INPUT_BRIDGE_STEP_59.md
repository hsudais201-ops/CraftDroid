# CraftDroid Step 59 — Input Bridge Verification

This step hardens the Android → embedded-Minecraft input path.

## Changes

- Added native input queue telemetry: queued, enqueued, dequeued, dropped, and coalesced counts.
- High-frequency mouse-motion and gamepad-axis events are coalesced instead of unnecessarily filling the queue.
- When the queue is full, older motion/axis events are discarded before discrete key/button events.
- GLFW polling no longer occurs while the global input mutex is held, preventing callback re-entry deadlocks.
- Added a Kotlin `NativeGameBridge.inputDiagnostics()` API and `InputBridge.diagnostics()` helper.
- Existing multi-touch, keyboard, gamepad, and customizable touch-control routing remains intact.

## Verification target

A healthy runtime should show `dropped=0` during normal input use. A non-zero drop count is diagnostic evidence of sustained queue pressure rather than an unexplained missing input event.
