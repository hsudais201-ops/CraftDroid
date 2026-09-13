# Step 193 — CI rebuild trigger

The Step 192 clean-install real-boot verification is prepared, but the repository integration does not expose a manual workflow-dispatch action through the connected GitHub tooling.

This commit intentionally changes a tracked repository file so the existing `push` trigger on `main` starts `Build CraftDroid APK` again. A successful build is then consumed by `Verify Real Minecraft Android Boot` through its `workflow_run` trigger.

## Verification target

- Build CraftDroid APK
- Direct Gradle 9.6.0 setup (no `gradle-wrapper.jar` dependency)
- APK x86_64 native-library preflight
- Fresh API 35 x86_64 emulator
- Clean-install launcher test
- Play/Start action discovery
- Post-Play diagnostics
- Proof of the real `net.minecraft.client.main.Main` process

A launcher process alone is not considered a Minecraft boot success.
