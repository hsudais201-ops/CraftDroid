# CraftDroid System Skin

## Goal
Provide a launcher-level default player skin selector without overriding official Microsoft account skins.

## UI
Profile -> Skin

Options:
- System Skin — CraftDroid's configured default skin
- Steve
- Alex
- Import Skin
- Remove Custom Skin

## Rules
- Imported skins must be PNG files.
- Accept standard Minecraft Java skin dimensions: 64x64 and 128x128.
- Persist the selected skin in launcher profile/config storage.
- Offline/local profiles use the selected launcher skin.
- Microsoft-authenticated profiles keep the official account skin unless the launcher has an explicit, supported account-skin override path.
- Invalid or unreadable images must show an error and leave the previous skin unchanged.
- Skin selection must not block Minecraft installation or launching.

## Architecture
Keep skin selection separate from the rendering/GLFW path. Resolve the effective skin when constructing the player/profile launch configuration, then pass only the resolved asset reference into the game integration layer.

## Acceptance criteria
1. Skin settings are reachable from Profile.
2. Steve and Alex can be selected and persisted.
3. A valid 64x64 or 128x128 PNG can be imported and persisted.
4. Invalid files are rejected safely.
5. Removing the custom skin restores System Skin.
6. Microsoft profiles do not have their official skin silently replaced.
7. Existing launcher build and runtime smoke tests remain green.
