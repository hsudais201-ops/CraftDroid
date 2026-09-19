# Step 145 Changes

- Surface replacement/destruction now clears the pending Android -> GLFW input queue while stopping the old input pump.
- Prevents stale touch, mouse, key, scroll, and character events captured for an old Android Surface from being replayed after Surface recreation/rotation.
- The persistent `g_input_requested` state is preserved so a live Minecraft JVM can still restore the input pump on the replacement Surface.
