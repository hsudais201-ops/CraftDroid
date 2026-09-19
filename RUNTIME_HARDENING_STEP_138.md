# CraftDroid Runtime Hardening — Step 138

- Prevented the native input pump from starting when the embedded JVM is no longer running.
- Cleared the persistent input-request flag immediately when `JLI_Launch` returns, before pump shutdown, so a concurrent Surface recreation cannot revive input dispatch for a dead VM.
- Cleared live GLFW input-ready state on JVM exit.

Validation remains limited to static/native-source checks and ZIP integrity in this environment; a full Android Gradle build, APK install, and real Minecraft boot still require a machine/CI runner with the Android SDK/NDK and Gradle dependencies.
