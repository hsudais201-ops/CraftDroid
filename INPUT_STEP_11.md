# CraftDroid Runtime Step 11 — Input/Event Pipe

Implemented Android input delivery fixes for the embedded Minecraft JVM.

## Changes

- The input pump no longer requires a native `g_glfw_window` just to deliver queued Android events to `CallbackBridge`. This matters when the Java GLFW stub owns the shared EGL context.
- Added explicit GLFW callback event mappings for:
  - Unicode character input (`EVENT_TYPE_CHAR` / 1000)
  - mouse wheel (`EVENT_TYPE_SCROLL` / 1007)
  - keyboard, mouse buttons and cursor position remain on the existing 1005/1006/1003 path
  - gamepad axis/button events remain supported
- Added `NativeGameBridge.sendChar()` and native Unicode event queuing.
- Added horizontal + vertical mouse-wheel forwarding from Android `MotionEvent.ACTION_SCROLL`.
- Android key-down events now forward `unicodeChar` to the Java GLFW callback bridge so Minecraft text fields/chat can receive actual character input.
- Kept the embedded HotSpot JVM as the only JVM used for callback delivery; Android ART JNI is not used for `CallbackBridge.receiveCallback`.

## Important

PojavLauncher also uses a dedicated CallbackBridge/input pipeline and a rewritten native input pipe. CraftDroid now follows the same separation: Android events are queued natively and dispatched on a thread attached to the embedded game JVM. This does not claim device-level Minecraft boot verification yet.
