# CraftDroid 2.4 Project Review

## Result

This ZIP is a real Android launcher project, but the original project was not yet a fully verified real-Minecraft runtime.

### Findings fixed in this revision

- Added the published SHA-256 for the Java 21 x86 Android runtime.
- Native stack validation now requires GLFW, LWJGL native core, PojavExec/AWT bridge, and a GL backend.
- Native runtime loading now loads `liblwjgl.so` before `libglfw.so`.
- Embedded JVM preloading now also checks `libjsig.so`.
- Removed stale wording that described the embedded JVM as a child Process.
- Native-stack install diagnostics are more explicit and cleanup removes the downloaded Pojav APK after extraction.

## Important remaining limitation

The project still cannot be declared universally boot-tested from source alone. A real Android device/emulator build is required to verify:

1. the selected Android OpenJDK actually executes on that ABI;
2. the downloaded native bridge matches that ABI and the Minecraft/LWJGL version;
3. the GPU-specific renderer works;
4. the selected Minecraft version reaches the title screen and accepts input.

The current native integration follows a Pojav-style design, but upstream Pojav's current releases have moved toward a real GLFW backend and per-version LWJGL handling. This project still uses its downloaded Android GLFW Java stub. Therefore support should be treated as version-dependent until device tests confirm it.

## Build environment

The ZIP includes `gradlew` and Gradle configuration, but the Gradle wrapper JAR is missing from the archive. This is a packaging/build issue, not a Minecraft runtime issue. The project also expects Android Studio/SDK/NDK to be installed.

Android Gradle Plugin 9.4.0 and Gradle 9.6.0 are a valid current combination.
