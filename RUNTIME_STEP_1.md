# CraftDroid runtime step 1 — Android OpenJDK/JLI

This update focuses on the first blocker in the Minecraft boot chain: the Android Java runtime.

## Changes

- Java 8 automatic installation is enabled again.
- Java 17, 21 and 25 continue using the pinned AngelAuraMC Android JRE release assets.
- Java 25 correctly rejects x86 because upstream does not publish a Java 25 x86 runtime.
- Runtime validation now requires both `lib/jli/libjli.so` and a JVM library (`lib/server/libjvm.so`, `lib/client/libjvm.so`, or `lib/libjvm.so`) before the runtime is considered valid.
- Minecraft's `LD_LIBRARY_PATH` now puts the JRE JLI/VM directories first, followed by renderer and Minecraft native directories.

The JRE distribution approach matches the current Android launcher ecosystem: Pojav/Amethyst builds use pre-built Android JREs and a separate custom LWJGL/GLFW layer rather than a normal desktop JDK. See the upstream build documentation.

## Not completed yet

This does **not** mean Minecraft can boot yet. The next step is the native GLFW/LWJGL stack and its ABI/dependency verification. A real Android device test is still required.

## Build check

The project could not be compiled in this environment because Gradle could not download its distribution (`services.gradle.org` DNS/network unavailable). No claim of a successful APK build is made.
