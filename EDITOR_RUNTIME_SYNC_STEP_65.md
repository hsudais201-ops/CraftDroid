# CraftDroid Step 65 — Live Control Editor / Runtime Synchronization

## What changed

- `LauncherContainer` is now an application-wide singleton, so MainActivity and GameActivity share the same `TouchInputManager`.
- The live overlay observes `currentLayout`, `orientation`, and `pressedControlIds` and redraws immediately when the editor changes a control.
- Control mutations request a debounced persistent save instead of waiting for the editor's manual SAVE button.
- Control profile persistence uses an atomic temporary-file replacement path and stores the active profile ID alongside the profile data while retaining the legacy active-profile file for compatibility.
- Orientation changes release active inputs before switching to the other layout, avoiding stale pointers/keys during rotation.

## Result

Edits made in Settings → Controls → Customize Controls are applied to the same runtime control manager used by the Minecraft GameActivity and are persisted automatically. Switching/restarting the launcher reloads the active profile and its latest saved controls.
