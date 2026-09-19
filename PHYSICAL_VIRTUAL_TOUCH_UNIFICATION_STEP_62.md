# CraftDroid Step 62 — Physical + Virtual Touch Unification

The GameActivity now obtains the shared LauncherContainer TouchInputManager InputBridge.
Raw Android MotionEvents are routed through the same touch manager used by virtual controls.

Rules:
- One primary physical pointer drives camera/mouse movement.
- Secondary pointers are tracked independently and never steal the primary pointer.
- Physical-touch button ownership uses namespaced virtual sources (`physical-touch-<pointerId>`).
- Virtual button ownership remains independent (`virtual:<controlId>`).
- Surface teardown releases both physical and virtual touch sources.
- This prevents physical and virtual input from cancelling one another unexpectedly.
