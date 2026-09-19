# CraftDroid Step 64 — Runtime Control Scaling, Orientation and Safe Areas

- Touch overlay density is refreshed when its size changes.
- Stored control positions remain normalized percentages, so layouts scale with the surface.
- Window status/navigation/display-cutout insets define a runtime safe rectangle.
- Control hit/draw bounds are clamped inside the safe rectangle without changing saved positions.
- GameActivity updates the active layout when Android reports an orientation change.
- Existing touch pointers are released on configuration changes to prevent stale coordinates.
- The GameActivity remains landscape-locked by the manifest, while the overlay code safely supports portrait layouts for the custom editor/runtime if the host configuration is changed later.
