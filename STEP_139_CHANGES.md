# Step 139 Changes — Terminal Native GLFW Shutdown Input State

- Hardened `craftdroid_glfw_shutdown()` so a full native GLFW teardown clears both:
  - the live `g_glfw_input_ready` state; and
  - the persistent `g_input_requested` state.
- These flags are cleared **before** joining/stopping the input pump, preventing a
  concurrent Android surface transition from observing stale callback intent and
  recreating an input dispatcher after native GLFW teardown.
- Pending input events are still discarded by the existing `stopInputPump(true)` path.
- This complements Step 138's JVM-exit cleanup: both embedded-JVM termination and
  explicit native GLFW shutdown now close the input lifecycle completely.
