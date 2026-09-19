# Step 124 changes

- Fixed a surface-transition input regression introduced by stopping the GLFW input pump before surface replacement.
- nativeSetSurface now remembers whether the callback/input pipe was active, stops the pump safely, replaces the surface/window, then restarts the pump after releasing g_mutex.
- Prevents a surface resize/rotation from leaving GLFW input permanently disabled.
- Failed input restart leaves the callback pipe explicitly disabled rather than reporting readiness without a dispatcher.
