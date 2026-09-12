# CraftDroid

Android Minecraft Java launcher project.

## Current state

- GitHub Actions Android build workflow: configured and tested through the source-repair/build/emulator pipeline.
- CraftDroid Android source tree: included inside `CraftDroid_Launcher_2.4_GitHubActions_Step153.zip`.
- Runtime hardening: Step 153-155 repairs are applied in CI for Kotlin/test/native compatibility.
- Android launcher runtime smoke test: verified previously on the GitHub Actions emulator pipeline.
- Automatic Java/renderer preparation contract: verified for Java 8/16/17/21/25 compatibility and native renderer setup.
- Real Minecraft 1.21.1 metadata fixture: PASS.
- Real Minecraft 1.21.1 installation fixture: PASS, including client JAR, asset index, Linux-applicable libraries, and native artifacts.
- Real Minecraft 1.21.1 launch fixture: PASS, including the real `net.minecraft.client.main.Main` class and a non-empty resolved classpath.
- APK build for commit `ac1af0575d76c399dcfed271a829e5917c32dca4`: the latest GitHub Actions run is currently pending after a retry; a new completed APK result has not yet been claimed.
- Real Minecraft game boot: not yet verified.

## Current next step

Step 181 is the real JVM-launch integration test. It must exercise the production launcher with actual Minecraft files on the Android emulator and capture the first JVM/GLFW failure or a successful Minecraft startup. Static fixtures and launcher contracts must not be reported as a full game boot.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
