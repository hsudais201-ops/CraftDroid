# CraftDroid Step 28 — Forge Legacy Compatibility Layer

This step hardens the Forge compatibility layer for historical installer formats.

## Changes
- Added an explicit `LEGACY_JAR_MOD` installer format to the format enum.
- Legacy Forge installers are detected by conservative archive inspection rather than being rejected solely because launcher profile JSON is absent.
- Detection recognizes Forge package namespaces plus historical Forge/ModLoader markers.
- Legacy Forge gets an isolated profile and patched client JAR while leaving the vanilla installation untouched.
- NeoForge legacy jar-mod archives are rejected explicitly because NeoForge's supported installer architecture is profile/processor based.
- Modern V1/V2 profile installers continue through the normal processor path.

## Important
This does not claim that every Forge build from Minecraft 1.1 onward is guaranteed to work. Forge's own documentation notes substantial differences among legacy versions and incomplete historical documentation. The launcher now selects a format-specific strategy instead of treating all historical installers identically.
