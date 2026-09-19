Step 96 - Embedded JVM stop/lifecycle recovery

- Prevented failed native Java-stop requests from leaving the bridge permanently in STOPPING state.
- If no live JavaVM is available, stop now restores RUNNING state before returning failure.
- Failed AttachCurrentThread() now restores RUNNING state.
- Missing java/lang/System.exit now restores RUNNING state.
- After JLI_Launch returns, stale g_game_vm ownership is cleared when no embedded VM remains.
- Keeps native lifecycle diagnostics consistent after normal or failed JVM shutdown.
