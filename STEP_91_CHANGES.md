# Step 91 Changes

## Native validation authority hardening

- Native LWJGL stack validation now inspects the exact `g_lwjgl_handle` and `g_lwjgl_library_name` recorded by `loadNativeStack()`.
- Removed filesystem-based `RTLD_NOLOAD` rediscovery of the selected LWJGL JNI library during validation.
- Native GLFW stack validation now requires the exact GLFW handle/name recorded by the stack loader instead of rediscovering a library from the native directory.
- GLFW/LWJGL validation now fails closed when the recorded handle or selected filename is missing or mismatched.
- This keeps runtime selection, loading, and validation on one authoritative native-handle path and prevents ABI drift when multiple GLFW/LWJGL variants are present.
