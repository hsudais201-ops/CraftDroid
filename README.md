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
- Step 181 real Android boot harness: added. It installs the latest available CraftDroid debug APK on an Android emulator, starts the production launcher entry point, captures JVM/GLFW/native diagnostics, and refuses to call launcher startup a full Minecraft boot.
- Real Minecraft game boot: not yet verified.

## Current next step

Step 181 now needs a completed GitHub Actions run against a staged Minecraft installation. The required success condition is a concrete Minecraft JVM launch/startup signal without fatal Java/native/GLFW errors; a healthy launcher process alone is not sufficient.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
