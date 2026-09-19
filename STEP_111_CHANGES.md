# Step 111 Changes

- Serialized embedded JavaVM pointer access with `g_mutex`.
- Input pump snapshots the embedded VM pointer before attaching and uses that stable local pointer for GetEnv/Attach/Detach.
- CallbackBridge.nativeSetInputReady records the VM under the same mutex.
- Native JLI exit clears the VM pointer under the mutex after the input pump is joined.
- nativeRequestJavaStop snapshots the VM pointer under the mutex.
- GLFW input-ready recheck is now synchronized instead of reading the flag unsafely after polling.
- This removes native data races around VM ownership and GLFW input state.
