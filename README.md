# CraftDroid Launcher 1.7

CraftDroid is an Android/Kotlin launcher project for Minecraft: Java Edition. It is designed around the same broad Android-Java architecture used by PojavLauncher: a mobile OpenJDK, an Android-compatible LWJGL/GLFW layer, renderer/native components, an Android game surface, and native input bridging.

## Build

- Android Studio
- JDK 17
- Android Gradle Plugin 9.4.0
- Gradle 9.6.0
- Android NDK 27.2.12479018

Open the project directory in Android Studio and build the `app` module.

## 1.7 changes

- Embedded OpenJDK launch through `libjli.so` / `JLI_Launch`.
- Android `SurfaceView` connected to a native `ANativeWindow` bridge.
- Pojav-style Android GLFW Java stub installed on demand and placed first on the Minecraft classpath.
- CraftDroid `CallbackBridge` patch loads the launcher JNI bridge and forwards keyboard/mouse events to the GLFW stub.
- Native renderer stack manager downloads upstream Pojav/MobileGlues components as needed.
- Java runtime downloads are verified and kept in app-private storage.
- Renderer environment and Android GLFW properties are prepared automatically.

## Important

This is a substantially more complete Android launcher foundation. It is **not guaranteed to run every Minecraft version on every Android GPU until a real Android device test passes**. The renderer/native stack is device-dependent, and the selected JRE must be an Android-compatible OpenJDK build.

The GLFW design follows PojavLauncher documentation: Pojav explicitly builds a custom `jre_lwjgl3glfw` stub for Minecraft 1.13+ rather than using desktop GLFW unchanged.

See:

- `EMBEDDED_JVM.md`
- `GAME_SURFACE.md`
- `LWJGL_GLFW_ANDROID.md`
- `NATIVE_GLFW_ADAPTER.md`
- `NATIVE_STACK.md`
- `BUILD_REVIEW.md`
- `THIRD_PARTY_NOTICES.md`

## CraftDroid 1.8 UI/UX update

The launcher UI has been polished for phones, tablets and Chromebooks:
- darker graphite gaming theme with consistent green/cyan accents
- clearer Home hero and account strip
- larger primary Play/Install action
- cleaner performance cards for Java, RAM, renderer and version
- launcher-status panel that distinguishes configuration readiness from real Minecraft rendering verification
- dedicated touch-controls shortcut
- more compact, consistent typography and navigation surface

The status panel intentionally does **not** claim that Minecraft rendering is verified. A real device launch is still required to validate the embedded JVM, Android GLFW bridge, EGL/OpenGL path and renderer.

## Account system

CraftDroid supports three account entries in the Accounts screen:

- **Microsoft** — official Minecraft authentication.
- **Ely.by** — Ely.by authentication where configured.
- **Offline / Local** — a local profile for offline or launcher testing. It does not create fake tokens, bypass Microsoft authentication, or unlock online Minecraft ownership.

The Accounts screen supports adding, selecting, renaming, removing, and persisting profiles.


### Offline / Local accounts
CraftDroid now treats Offline / Local as a first-class local profile: the username is validated, a stable offline UUID is generated, the profile persists across launches, and the JVM receives the conventional local `legacy` user type with access token `0`. This does not forge Microsoft authentication or ownership.


## Latest runtime hardening

Step 45 hardens embedded Android OpenJDK/JLI native startup and validates the JLI/JVM library boundary before Minecraft launch.


### Step 48
LWJGL/GLFW Java-native handshake added before embedded JLI launch.


## Step 63
Runtime touch controls are now composed directly above the Android Minecraft GameSurface. The overlay draws the saved control profile and routes button, joystick, camera/look, and empty-surface touches through the shared TouchInputManager without creating another render surface.
