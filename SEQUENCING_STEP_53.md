# CraftDroid Step 53 — Java-to-renderer startup sequencing

This step hardens the handoff from the Android `Surface` to EGL/GLES, GLFW, and the embedded Minecraft JVM.

## Changes
- Added a native surface-generation counter.
- Added one atomic graphics preparation transaction: validate the current Surface dimensions, create/reuse EGL, make it current, clear/finish/swap one GLES frame, and resolve GLFW symbols.
- The launch manager captures the Surface generation before preparation and verifies it again after preparation and immediately before JLI startup.
- The JVM is never started when the Android Surface was replaced or resized during preparation.
- Existing shared-EGL GLFW properties remain JVM options inserted before `-cp`.
- No second GLFW window or EGL context is created.

## Verification
Static source checks should confirm the new JNI methods, generation guard, and graphics transaction are present. A CI/device run is still required to prove an actual Minecraft frame is rendered by the game itself.
