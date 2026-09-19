# Step 51 — Renderer-specific runtime initialization

CraftDroid now performs a final renderer backend gate after the Android native stack is installed and before the embedded JVM starts.

## Checks
- GL4ES: requires an installed GL4ES native library.
- MobileGlues: requires MobileGlues and detected GLES 3+.
- Zink: requires a detected Vulkan device and an installed Zink/Mesa native backend.
- Compatibility mode: safe fallback without a third-party renderer.

A backend that is unsupported by the installed runtime cannot silently proceed to Minecraft. Zink/MobileGlues may fall back to GL4ES when that fallback is available.

This step reduces renderer-startup `UnsatisfiedLinkError`/missing-library failures and makes the selected backend deterministic before JVM startup.
