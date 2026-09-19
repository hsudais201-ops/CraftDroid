# Step 137 changes

- Hardened JNI input callback delivery against `NewLocalRef()` failure.
- Clears a pending JNI exception when a local `CallbackBridge` reference cannot be created, preventing an unrelated pending exception from poisoning the embedded Minecraft callback path.
- The current input event is dropped safely and subsequent events can retry delivery.
- Preserved the existing global-reference lifetime protection and event queue behavior.
