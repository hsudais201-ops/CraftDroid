# Step 100 changes

- Hardened embedded JVM shutdown to use only the exact HotSpot VM handle captured by CallbackBridge.nativeSetInputReady().
- Removed JNI_GetCreatedJavaVMs() fallback, preventing accidental shutdown of Android ART instead of the embedded game VM.
- Added Java-exception handling around System.exit(); failed shutdown requests restore RUNNING state instead of falsely reporting success.
- Preserved the existing terminal-on-exit semantics and stale-VM cleanup from Step 99.
