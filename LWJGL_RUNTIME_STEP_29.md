# Step 29 — LWJGL runtime profile selection

CraftDroid now selects the Android LWJGL compatibility family from the resolved Minecraft metadata.

- Minecraft 1.12.2 and older: LWJGL2 compatibility profile (lwjglx/lwjgl2 marker expected when available).
- Minecraft 1.13 and newer: LWJGL3 + Android GLFW stub profile.
- Native LWJGL diagnostics now record the selected family.
- GLFW stub installation is skipped for the legacy family.
- The vanilla and mod-loader version metadata remain the source of truth for Java LWJGL artifacts.

This follows PojavLauncher’s documented split: 1.12.2 and below use the LWJGL2 compatibility layer, while 1.13+ uses the GLFW stub. It does not claim that a generic Android `liblwjgl.so` is ABI-compatible with every LWJGL release; real-device validation is still required.
