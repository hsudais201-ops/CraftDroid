# Step 114 changes

- Removed the incorrect surface-resize event injection from `nativeSetSurface()`.
- Surface updates are state changes (`g_window`, `g_width`, `g_height`, generation), not mouse events.
- Prevents Android resize/rotation callbacks from being delivered through `InputEvent` type 1 as fake mouse movement.
- Keeps the bounded/coalescing input queue dedicated to actual input events.
