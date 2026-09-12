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
- Step 184 clean-install boot harness: creates CraftDroid's app-private game root when a fresh install has no pre-existing `versions/` directory, then stages the real Minecraft 1.21.1 fixture.
- Step 185 Play-action discovery: waits for the production launcher UI and finds Play/Start by either visible text or content description before tapping it, reducing false failures caused by Compose/accessibility node differences.
- Real Minecraft game boot: not yet verified in a completed Android emulator run.

## Current next step

Complete the Step 185 Android emulator run. If it reaches the production launch path, use the captured diagnostics to repair the first concrete Minecraft JVM, Java runtime, native renderer, GLFW, or launcher-path failure. A healthy launcher process alone does not count as Minecraft boot.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
