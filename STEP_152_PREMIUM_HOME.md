# Step 152 — Premium Game-Style Home Shell

- Reworked the CraftDroid home screen into a premium game-launcher dashboard.
- Added configurable title/subtitle, accent colors, and background brush parameters.
- Added animated ambient background accents without requiring image assets.
- Added profile/account capsule and top notification badge.
- Added launcher-local resource display for Coins, Gems, and Energy.
- Added prominent animated Play / Download button with press and hover scaling.
- Added Quick Access row for Settings, Store, Events, Leaderboard, and Profile.
- Store/Events/Leaderboard/Notifications currently use safe informational dialogs rather than pretending to be connected online services.
- Preserved existing Minecraft version, Java, RAM, renderer, install, repair, account, skin, health, and touch-control navigation.
- Kept the screen responsive through Compose layout primitives and weight-based action sizing.
