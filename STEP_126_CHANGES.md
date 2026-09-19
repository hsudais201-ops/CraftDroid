# Step 126 changes

- Fixed a real input-pump startup deadlock in `craftdroidbridge.cpp`.
- The callback-cache failure path previously called `failStartup()` while holding `g_mutex`; `failStartup()` also acquires `g_mutex`, which could deadlock when `CallbackBridge` lookup/global-reference creation failed.
- Startup now computes callback readiness under the mutex, releases the mutex, then performs failure cleanup.
- Also handles `NewGlobalRef()` failure explicitly so a null global reference cannot be treated as a valid callback cache.
- ZIP integrity check passed.
