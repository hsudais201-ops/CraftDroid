# Droid Launcher

Android Minecraft Java launcher project.

## Product name

**Droid Launcher**

The GitHub repository remains `CraftDroid`, while the Android application and launcher-facing branding use the product name **Droid Launcher**.

## Current state

- GitHub Actions Android build workflow: configured through the source-repair/build/emulator pipeline.
- Droid Launcher Android source tree: included inside `CraftDroid_Launcher_2.4_GitHubActions_Step153.zip`.
- Runtime hardening: Step 153-155 repairs are applied in CI for Kotlin/test/native compatibility.
- Android launcher runtime smoke test: verified on the GitHub Actions emulator pipeline.
- Automatic Java/renderer preparation contract: verified for Java 8/16/17/21/25 compatibility and native renderer setup.
- Real Minecraft 1.21.1 metadata fixture: PASS.
- Real Minecraft 1.21.1 installation fixture: PASS, including client JAR, version JSON, asset index, Linux-applicable libraries, and native artifacts.
- Real Minecraft 1.21.1 launch fixture: PASS, including the real `net.minecraft.client.main.Main` class and a non-empty resolved classpath.
- Step 184 clean-install boot harness: creates Droid Launcher's app-private game root when a fresh install has no pre-existing `versions/` directory, then stages the real Minecraft 1.21.1 fixture.
- Step 185 Play-action discovery: waits for the production launcher UI and finds Play/Start by either visible text or content description before tapping it, reducing false failures caused by Compose/accessibility node differences.
- Step 190 launch-boundary diagnostics: clears both normal and crash logcat immediately before the Play/Start action so pre-launch noise cannot create a false launch result.
- Step 191 clean-install verification: uninstalls the APK before installation, eliminating stale app data as a source of false positives/negatives during real-boot testing.
- Real Minecraft game boot: not yet verified in a completed Android emulator run.

## Current next step

Run the Step 191 clean-install Android emulator verification. If it reaches the production launch path, use the captured post-Play diagnostics to repair the first concrete Minecraft JVM, Java runtime, native renderer, GLFW, or launcher-path failure. A healthy launcher process alone does not count as Minecraft boot.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
