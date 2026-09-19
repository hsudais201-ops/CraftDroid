# CraftDroid Launcher — Step 74

## Embedded JVM / native startup hardening

- Fixed Android OpenJDK discovery so `libjli.so` can be found in both
  `lib/jli/` and multi-architecture layouts such as `lib/aarch64/jli/`,
  `lib/arm/jli/`, `lib/x86_64/jli/`, and `lib/i386/jli/`.
- Expanded the runtime native search path passed by the launcher to include
  architecture-specific JRE directories and every configured Android native
  stack directory, not only the first native directory.
- Added `CRAFTDROID_NATIVE_LIBRARY_PATH` to the embedded-JVM environment for
  diagnostics and native backend discovery.
- Fixed the GLFW/LWJGL handshake to recognize both `liblwjgl.so` and
  `liblwjgl3.so`, matching the native loader's supported filenames.
- Preserved the Android/Pojav-compatible `-Djdk.lang.Process.launchMechanism=FORK`
  behavior; PojavLauncher uses this on Android because the default POSIX spawn
  path requires `jspawnhelper`, which does not work on Android.

This step specifically targets the runtime layouts and native library-loading
contract that must succeed before Minecraft's main class can start.
