# CraftDroid

Android Minecraft Java launcher project.

## Current state

- GitHub Actions Android build workflow: configured through the source-repair/build/emulator pipeline.
- CraftDroid Android source tree: included inside `CraftDroid_Launcher_2.4_GitHubActions_Step153.zip`.
- Runtime hardening: Step 153-155 repairs are applied in CI for Kotlin/test/native compatibility.
- Android launcher runtime smoke test: verified on the GitHub Actions emulator pipeline.
- Automatic Java/renderer preparation contract: verified for Java 8/16/17/21/25 compatibility and native renderer setup.
- Real Minecraft 1.21.1 metadata fixture: PASS.
- Real Minecraft 1.21.1 installation fixture: PASS, including client JAR, version JSON, asset index, Linux-applicable libraries, and native artifacts.
- Real Minecraft 1.21.1 launch fixture: PASS, including the real `net.minecraft.client.main.Main` class and a non-empty resolved classpath.
- Step 182 real Android boot harness: stages the real Minecraft 1.21.1 fixture into CraftDroid's app-private game root and exercises the production launcher Play/Start path while collecting JVM/GLFW/native diagnostics.
- Step 183 CI reliability: real-boot verification is triggered independently on pushes and waits for a successful CraftDroid APK artifact built from the exact same commit, preventing build/verification race-condition skips.
- Real Minecraft game boot: not yet verified in a completed Step 182/183 Android run.

## Current next step

Complete the Step 183 Android emulator run and use its diagnostics to fix the first concrete Minecraft JVM, Java runtime, native renderer, GLFW, or launcher-path failure that appears. A healthy launcher process alone does not count as Minecraft boot.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
