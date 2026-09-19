# CraftDroid Android Native Stack

CraftDroid now has a native-component manager that downloads the Android native bridge at first launch instead of embedding another launcher's APK in CraftDroid.

## Components

- PojavLauncher native bridge: GLFW / PojavExec / OpenGL / audio and related Android native libraries.
- MobileGlues 2.0.0: downloaded from the upstream MobileGlues release and SHA-256 verified.
- Per-device ABI extraction: `arm64-v8a`, `armeabi-v7a`, `x86_64`, and `x86`.
- Runtime environment: `POJAV_NATIVEDIR`, `DRIVER_PATH`, `POJAV_RENDERER`, `POJAVEXEC_EGL`, `LIBGL_EGL`, `LD_LIBRARY_PATH`, AWT surface dimensions and compatibility flags.

## Important

The native stack is downloaded on demand and is not redistributed as part of CraftDroid. Keep the upstream license notices in `THIRD_PARTY_NOTICES.md` and review upstream licenses before publishing a release.

The native bridge is only one part of Minecraft-on-Android. The launcher still needs a compatible Android OpenJDK, Minecraft version assets/libraries, and a window/surface bridge matching the selected GLFW build. Do not claim all Minecraft versions are supported just because the APK builds.

## Renderer modes

- **MobileGlues**: preferred when the device exposes OpenGL ES 3.x.
- **GL4ES**: compatibility backend for older GLES environments.
- **Zink**: Vulkan-backed OpenGL path when selected and supported.

CraftDroid sets the same family of environment variables used by Android Java launchers, including `POJAV_RENDERER`, `POJAVEXEC_EGL`, `LIBGL_ES`, `LIBGL_EGL`, `POJAV_NATIVEDIR`, and `DRIVER_PATH`.
