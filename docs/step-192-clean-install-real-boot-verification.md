# Step 192 — Clean-install real Minecraft boot verification

## Objective

Run the production CraftDroid APK through the GitHub Actions Android emulator after a clean install, then use post-Play diagnostics to identify the first real Minecraft JVM/runtime/native/GLFW failure.

## Acceptance criteria

1. The APK is built successfully with the direct Gradle 9.6.0 CI setup.
2. The APK passes the x86_64 native-library preflight.
3. The real-boot workflow installs the APK on a fresh API 35 x86_64 emulator.
4. The launcher reaches the production Play/Start action.
5. Diagnostics are captured immediately before and after Play/Start.
6. Success requires evidence that the real `net.minecraft.client.main.Main` process starts; a healthy launcher process by itself is not sufficient.

## Current state

The repository already contains the Android build workflow, the real-boot workflow, and the Step 153–191 CI repairs. The latest real-boot attempt was skipped, so this commit intentionally triggers the normal `Build CraftDroid APK` workflow again; a successful build then feeds the real-boot workflow through `workflow_run`.
