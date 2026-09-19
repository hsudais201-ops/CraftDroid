# CraftDroid Step 57 — Minecraft game-state detection

This step separates Java/JVM startup from actual client/game-state evidence.

## Added state milestones

- `RENDERING`: CraftDroid has observed successful Android-surface frame swaps while Minecraft initialization markers are present.
- `MENU_READY_INFERRED`: resource + audio initialization and a live render loop are present, with no world-loading marker. This is deliberately labeled **inferred** because Minecraft versions do not expose one universal title-screen log message.
- `IN_GAME_DETECTED`: a world/game marker such as joining/loading/preparing spawn was observed while the render loop is active.

## Safety

The detector never treats the pre-launch GLES test as Minecraft rendering evidence. A frame count must advance while the embedded JVM is active.

This is a runtime diagnostic milestone, not a visual screenshot/title-screen proof.
