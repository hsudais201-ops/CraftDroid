# Native LWJGL ABI — Step 10

CraftDroid now validates the Android `liblwjgl.so` before starting Minecraft.

## What changed

- Detects the LWJGL versions declared by the selected Minecraft version.
- Requires a real Android `liblwjgl.so` in the CraftDroid native stack.
- Fingerprints the native binary for an embedded LWJGL version when available.
- Rejects an explicit native/Java LWJGL release-line mismatch (for example 3.2.x vs 3.3.x).
- Keeps the CraftDroid Android native directory first in `java.library.path` and `LD_LIBRARY_PATH`, so Mojang desktop natives do not accidentally win the native-loader race.
- Logs the native ABI decision before `JLI_Launch`.

## Important limitation

A binary without an embedded version string cannot be proven compatible by a static fingerprint alone. CraftDroid therefore reports that case as `unknown-but-allowed`; real-device launch testing is still required.

Current TeamPojavLauncher releases use a version-appropriate LWJGL setup and automatically install suitable LWJGL versions, which is the model CraftDroid is moving toward. See the official release notes for that architecture change.
