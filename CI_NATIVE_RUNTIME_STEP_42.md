# CraftDroid Step 42 — Native Dependency Resolution

This step hardens the Android native runtime layer.

## Fixed

- Fixed `inspectInstalled()` so it looks in the actual versioned runtime path: `lwjgl/<version>/<abi>`.
- Native loading now matches library stems instead of assuming exact filenames.
- Added support for upstream variants such as `libglfw3.so` and versioned helper libraries.
- Added a dependency scan that attempts remaining bundled `.so` files before final GLFW/LWJGL validation.
- Native load failures are logged individually instead of silently hiding which `.so` failed.
- Final JNI validation remains the hard gate for GLFW/LWJGL compatibility.

## Why this matters

A Minecraft Android runtime is not just one `liblwjgl.so`. Native libraries have `DT_NEEDED` dependencies, and upstream Pojav/Mesa/OpenAL packages can change helper-library filenames between releases. The previous exact-name loader could therefore leave a required dependency unloaded even when it was present in the runtime directory.

## Verification

The source tree and generated ZIP were checked after modification. Full Gradle/APK execution is still dependent on an environment with the project's Android/Gradle dependencies available.
