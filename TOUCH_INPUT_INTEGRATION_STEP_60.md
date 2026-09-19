# CraftDroid Step 60 — Touch Controls to Minecraft Input Integration

Implemented source-aware virtual input routing.

## Changes
- Virtual keyboard keys are owned by a control source instead of sharing one global boolean state.
- Multiple virtual controls mapped to the same Minecraft key no longer release each other prematurely.
- A virtual control can coexist with a physical keyboard press of the same key; releasing the virtual control no longer releases the physical key.
- Virtual mouse buttons use the same source-ownership model. This prevents two independent virtual controls from incorrectly releasing a shared mouse button.
- Movement joystick keys use a dedicated `joystick` source and cannot cancel a physical keyboard W/A/S/D press when the joystick returns to center.
- The in-game Compose control pointer token is no longer based only on the control ID hash, avoiding simultaneous-press collisions.
- Existing camera-look and gamepad paths remain separate.

## Verification
- Source-level brace/delimiter checks passed.
- No Gradle build was claimed because the local environment lacks the Gradle distribution/network needed to execute the Android build.
