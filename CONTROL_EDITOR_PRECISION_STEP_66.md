# CraftDroid Step 66 — Control Editor Drag/Resize Precision

- Editor dragging now uses the latest control state for every gesture delta, preventing long drags from jumping or losing movement when StateFlow emits updates.
- Selected controls expose an independent bottom-right resize handle.
- Resize changes width/height in dp with 24..400 dp bounds.
- Resize gestures are separate from move gestures.
- Existing grid/snap behavior remains applied through TouchInputManager.updateControl().
- Existing normalized positions and density-aware runtime rendering are preserved.
- This step is source-level verified; a full Android Gradle build still requires the project's CI/toolchain environment.
