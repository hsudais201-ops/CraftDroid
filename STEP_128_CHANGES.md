# Step 128 changes

- Prevented the native input-pump thread from calling `glfwPollEvents()` when a different thread owns the GLFW/render context.
- GLFW polling is now restricted to the established GLFW owner thread.
- Android input events continue through CraftDroid's bounded queue and `CallbackBridge` dispatcher.
- This removes a thread-affinity race that could cause native crashes or undefined GLFW behavior on Android.
