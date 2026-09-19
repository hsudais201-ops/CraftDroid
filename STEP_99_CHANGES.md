# Step 99 – Embedded JVM handle cleanup

## Native bridge fix
- Removed post-`JLI_Launch` `JNI_GetCreatedJavaVMs` rediscovery.
- `g_game_vm` is now cleared unconditionally when the embedded JVM exits.
- Prevents CraftDroid from retaining or rediscovering Android ART's VM as if it were the embedded HotSpot VM.
- Prevents later stop/input operations from targeting a stale or wrong JavaVM.

## Verification
- Native source consistency: PASS
- ZIP integrity: PASS
- Full Gradle/APK build: still blocked by environment network/DNS restrictions.
