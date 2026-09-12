# CraftDroid

Android Minecraft Java launcher project.

## Current state

- GitHub Actions Android build workflow: configured through the source-repair/build/emulator pipeline.
- CraftDroid Android source tree: included inside `CraftDroid_Launcher_2.4_GitHubActions_Step153.zip`.
- Runtime hardening: Step 153-155 repairs are applied in CI for Kotlin/test/native compatibility.
- Android launcher runtime smoke test: verified on the GitHub Actions emulator pipeline.
- Automatic Java/renderer preparation contract: verified for Java 8/16/17/21/25 compatibility and native renderer setup.
- Real Minecraft 1.21.1 metadata fixture: PASS.
- Real Minecraft 1.21.1 installation fixture: PASS, including client JAR, asset index, Linux-applicable libraries, and native artifacts.
- Real Minecraft 1.21.1 launch fixture: PASS, including the real `net.minecraft.client.main.Main` class and a non-empty resolved classpath.
- Step 182 real Android boot harness: added. It materializes the real Minecraft 1.21.1 fixture, discovers CraftDroid's app-private `versions` root, stages the client/version JSON/libraries/assets there, installs the matching debug APK from the successful Android build, and exercises the production launcher Play/Start path while collecting JVM/GLFW/native diagnostics.
- Real Minecraft game boot: requires a completed successful Step 182 run with a concrete production launch marker and no fatal Java/native/GLFW errors.

## Current next step

Run Step 182 to completion in GitHub Actions. A healthy launcher process alone does not count; success requires the staged real 1.21.1 installation to reach the production Minecraft launch path without fatal Android/JVM/native errors.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
