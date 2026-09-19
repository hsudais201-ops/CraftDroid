# CraftDroid Step 68 — Gesture-Aware Editor History

The control editor now treats a continuous drag or resize as one undoable action instead of creating a history entry for every pointer-move event.

## Changes
- Added `beginEditorGesture()`, `endEditorGesture()`, and `cancelEditorGesture()` to `TouchInputManager`.
- Drag and resize gestures start a history transaction.
- Intermediate `updateControl()` calls do not flood the undo stack while a gesture is active.
- Releasing the gesture creates one undo entry containing the layout from before the gesture.
- Cancelling a gesture restores the pre-gesture layout.
- Existing add/delete/duplicate/inspector edits continue to create normal history entries.

## Result
Undo/redo is substantially more predictable when precisely positioning or resizing controls, especially on touchscreens where a single drag produces many MotionEvent updates.
