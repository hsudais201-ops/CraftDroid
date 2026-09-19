# Step 110 Changes

- Fixed a real deadlock introduced by the bounded surface-event queue change.
- `nativeSetSurface()` already holds `g_mutex`; it now calls `pushLocked()` instead of the public `push()` wrapper, which would recursively lock the same mutex.
- Kept all other input paths on the normal locking `push()` wrapper.
- Preserved the `MAX_EVENTS` bound and motion/axis coalescing behavior.
