# Step 141 Changes — Native Surface Lifecycle State Guard

- Hardened `nativeSetSurface()` to consult the full embedded-JVM lifecycle state, not only `g_java_running`.
- Surface teardown/replacement is now rejected during `STARTING`, `RUNNING`, and `STOPPING` states.
- `EXITED` remains permitted so deferred Android Surface cleanup can proceed after `JLI_Launch` returns.
- This closes the small window where `g_java_running` could still be false while the embedded JVM lifecycle had already entered `STARTING` or had begun `STOPPING`.
