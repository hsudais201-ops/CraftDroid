# CraftDroid Launcher — Step 71

## Runtime compatibility fixes

- Removed the false exact-version gate between Android `liblwjgl.so` and Maven desktop LWJGL coordinates. Android LWJGL ports may use a different patch string or be stripped.
- Kept ABI/ELF validation and the real JNI GLFW handshake as launch gates.
- Recognized both `liblwjgl.so` and `liblwjgl3.so` in native-stack discovery.
- Expanded Android/system native dependency allow-list to reduce false failures on vendor Android images.

## Why this matters

The previous validation could download a valid native stack and then reject it solely because a version string embedded in the Android binary did not exactly equal the Java Maven version. Step 71 removes that false negative while retaining the checks that can actually establish loadability.
