# CraftDroid Step 61 — Multitouch Control Routing

## Changes

- Added monotonic launcher-owned pointer tokens for Compose virtual controls.
- Removed timestamp/object-identity pointer ID synthesis, which could collide under rapid simultaneous gestures.
- Made pointer ownership idempotent with `putIfAbsent`.
- Guaranteed button release in a `finally` block when a gesture is cancelled.
- Added a controlled release path for all active virtual control pointers.
- Existing per-control ownership means two fingers can hold two controls at once; duplicate presses on the same control are reference-counted by pointer ownership.
- Joystick and camera gestures retain separate state, so camera movement can continue while a movement/action control is held.

## Limitation

The Android game surface still has its own physical-touch mouse routing. The virtual control overlay is independent of that path; the next input-layer work can unify the physical and virtual camera modes if desired.
