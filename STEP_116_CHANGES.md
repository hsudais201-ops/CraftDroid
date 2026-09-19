Step 116 - Native GLFW input-ready race fix

Fixed a real data race around g_glfw_input_ready. The flag was a plain bool read from the input pump, GLFW callback delivery, and diagnostics while other threads could write it during shutdown/startup. It is now an atomic<bool> with acquire/release access, preventing stale or torn readiness observations during surface/JVM lifecycle transitions. No behavior change to the callback protocol was intended.
