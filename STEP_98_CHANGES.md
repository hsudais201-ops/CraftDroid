# Step 98 changes

- Corrected the embedded JVM lifecycle model introduced in Step 97.
- HotSpot/JNI VM creation is treated as process-lifetime state: EXITED is terminal and cannot be reused for a second JLI_Launch in the same process.
- Added explicit native error code `-108` and a clear launcher log/error path for this unsupported restart case.
- Kept the previous diagnostics state so the UI can report that the JVM exited.
- Fixed launch-manager logging to retain the post-JLI bridge state in a local value.
