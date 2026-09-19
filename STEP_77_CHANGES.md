# CraftDroid Step 77 – Native GLFW handshake mode fix

- The native GLFW handshake now accepts an explicit `requireCallbackBridge` mode.
- Modern LWJGL3/native-GLFW launches no longer fail merely because the legacy CallbackBridge JNI exports are absent or partial.
- Legacy GLFW-stub launches still require the complete CallbackBridge JNI contract.
- LaunchManager passes the LWJGL runtime profile into the handshake, so the check matches the actual Java GLFW strategy.
- Improved logs distinguish legacy-stub and native-GLFW graphics preparation.
- Kept the LWJGL JNI_OnLoad and core GLFW symbol checks mandatory.
