# Step 35 — APK Smoke Test

CraftDroid CI now performs an Android emulator smoke test after building the debug APK.

Checks:
- API 35 x86_64 emulator boots.
- APK installs successfully.
- `com.example.game` launches.
- The process remains alive for the startup window.
- Package metadata is readable.
- Logcat is captured for diagnosis.

This validates Android application startup only. It does not prove that a Minecraft version reaches the title screen or that native rendering works on physical hardware.
