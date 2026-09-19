# Step 30 — Per-version Android LWJGL Native Acquisition & Verification

CraftDroid now treats Android LWJGL natives as versioned runtime packages instead of one global `liblwjgl.so`.

## Runtime flow

1. Resolve the Minecraft Java-side LWJGL version from the normalized version metadata.
2. Select a package cache directory using `LWJGL version + Android ABI`.
3. Reuse the cached package only when the native LWJGL version matches exactly.
4. If the package is missing, download the current official TeamPojavLauncher release APK and extract only the selected Android ABI's native libraries.
5. Verify the resulting `liblwjgl*.so` fingerprint against the required runtime.
6. Never substitute a different LWJGL release line/version merely because the library exists.
7. Legacy Minecraft (LWJGL2 API compatibility) uses the known Android LWJGL3 compatibility runtime 3.3.3 rather than treating the desktop LWJGL2 version as an Android native ABI version.

## Safety behavior

A package with an unknown or mismatched native LWJGL version is rejected before JVM startup. This avoids turning an ABI/version mismatch into an opaque `UnsatisfiedLinkError` or native crash.

## Important limitation

The official Pojav project currently describes automatic per-game LWJGL installation and a custom Android/iOS LWJGL build. CraftDroid currently obtains its Android native bridge from the TeamPojavLauncher release APK, so if that APK does not contain the exact requested LWJGL native version, CraftDroid stops rather than silently using an incompatible binary. A future package manifest can add additional officially built native packages without changing the verification logic.
