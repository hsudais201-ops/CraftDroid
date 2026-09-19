# CraftDroid Step 38 — Selective Installation Repair

Step 38 adds an automatic repair pass between installation verification and JVM startup.

## What it repairs

- Missing or corrupted Minecraft client JAR
- Missing/corrupted asset index
- Missing/corrupted library artifacts
- Missing/corrupted native archives
- Missing/corrupted content-addressed asset objects
- Re-extraction of native `.so`/`.dll`/`.dylib` files after a native archive repair

Every download is tied to the URL, expected size, and SHA-1 supplied by the selected version metadata. The repair pass is selective; it does not redownload a healthy installation.

## Launch flow

`verify -> selective repair -> verify again -> classpath preflight -> native/JVM launch`

If the second verification still fails, CraftDroid refuses to launch and reports the remaining artifacts instead of knowingly starting with a broken installation.

## Important limitation

This repairs Minecraft artifacts described by version metadata. It does not magically repair an incompatible Android renderer or an incorrect Android LWJGL native build. Those still require exact native-stack compatibility validation.

PojavLauncher similarly separates the Android JRE/native stack from Minecraft libraries and supports multiple LWJGL/runtime paths; its documentation also warns that mismatched Java/native LWJGL versions can cause loader failures. See the upstream project for architecture context.
