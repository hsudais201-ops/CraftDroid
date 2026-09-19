Step 143 - Input pump self-shutdown hardening

- Removed self-detach behavior from stopInputPump().
- When the pump thread requests its own stop, it now sets the stop flag and returns without detaching.
- A later non-pump lifecycle call joins the still-joinable thread, preserving deterministic native-state lifetime.
- Prevents a detached input thread from racing with CallbackBridge/global-ref, GLFW, or JVM teardown.
