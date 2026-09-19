# Step 129 changes

## JNI callback lifetime race fixed

`deliverToGlfw()` previously copied the raw `CallbackBridge` global-reference handle, released `g_mutex`, and then invoked JNI. The input-pump shutdown path can delete that global reference immediately after the mutex is released, leaving the dispatcher with a stale JNI reference.

The dispatcher now creates a JNI local reference while holding `g_mutex`, uses that stable local reference for the callback invocation, and deletes it afterward. This prevents `DeleteGlobalRef()` in the shutdown/restart path from racing the callback dispatch.
