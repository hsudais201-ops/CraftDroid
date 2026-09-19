# Renderer Integration — Step 14

CraftDroid now has a conservative renderer compatibility policy between the selected Minecraft version, Android GPU capabilities, and the installed native renderer stack.

## Policy
- **GL4ES** remains the broad fallback.
- **MobileGlues** is selected only for modern LWJGL3 Minecraft on GLES 3-capable devices.
- **Zink** is selected only when Vulkan is available and the version is modern; if the native stack does not contain a recognizable Zink/Mesa backend, CraftDroid falls back to GL4ES instead of starting with an incomplete renderer.
- **Compatibility Mode** remains explicitly selectable.
- Renderer selection is logged with the requested backend, effective backend, and reason.

## Native stack safety
The native stack inspection now records whether Zink/Mesa components are actually present. This prevents a Zink environment from being requested when only GLFW/LWJGL/GL4ES libraries were installed.

## Important limitation
This is compatibility policy and native-library validation, not a device-specific guarantee. Zink/MobileGlues compatibility still depends on the Android GPU/Vulkan driver and the exact Minecraft/mod combination. Real-device testing is required.
