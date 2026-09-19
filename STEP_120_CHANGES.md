# Step 120 changes

- Hardened CallbackBridge embedded JVM handle retention.
- A transient `JNIEnv::GetJavaVM()` failure no longer clears the already-captured HotSpot `JavaVM*`.
- If a callback presents a different VM, CraftDroid keeps the original embedded VM handle rather than switching runtimes.
- This protects the GLFW input pump and native stop path from losing or replacing the active JVM identity.
