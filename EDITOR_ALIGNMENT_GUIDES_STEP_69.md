# CraftDroid Step 69 — Editor Alignment Guides

Implemented a visual precision layer for the touch-control editor.

## Changes
- Added center alignment guides for the selected control.
- Added a center-point marker so the control's exact anchor is easy to see.
- Guides are visual-only and never modify the saved control coordinates.
- Preserved free-form drag and the existing optional grid/snap system.
- Fixed the Step 68 resize callback dependency by passing `TouchInputManager` explicitly into `ControlRenderItem`.

## Result
The editor now has both coarse grid/snap positioning and precise visual center alignment, while keeping existing control profiles and runtime behavior unchanged.
