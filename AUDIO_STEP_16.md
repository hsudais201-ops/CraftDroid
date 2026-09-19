# Audio Integration — Step 16

CraftDroid now validates and prepares Android OpenAL before starting Minecraft.

## Changes
- Added `AudioCompatibilityManager`.
- Requires a packaged Android `libopenal.so` (or compatible OpenAL library).
- Detects Minecraft's LWJGL OpenAL binding when present.
- Exposes the Android native OpenAL directory to LWJGL through the launch environment.
- Sets `CRAFTDROID_OPENAL` and `CRAFTDROID_OPENAL_LIBRARY` diagnostics.
- Configures OpenAL Soft without forcing a desktop audio backend.
- Fails early with a clear error when the Android OpenAL library is missing.

PojavLauncher documents OpenAL as part of its Android runtime and states that OpenAL works on most supported devices. The current Pojav project also lists OpenAL-Soft and Oboe among its audio components.
