# CraftDroid Step 22 — Mod Discovery & Compatibility Preflight

Implemented a safe pre-launch mod scanner.

## Added
- Scans enabled `.jar` files in the Minecraft `mods/` directory.
- Detects common metadata formats without executing mod code:
  - Fabric: `fabric.mod.json`
  - Forge/NeoForge: `META-INF/mods.toml`
  - Legacy Forge: `mcmod.info`
- Detects the selected loader from the resolved Minecraft version profile.
- Flags obvious Fabric/Forge/NeoForge loader mismatches.
- Flags obvious Minecraft-version metadata mismatches when a mod declares a concrete version.
- Warns about duplicate mod IDs.
- Disabled `.jar.disabled` files remain ignored.
- Launch is stopped before JVM startup when a clear mod compatibility error is found.

## Safety
This step only reads JAR metadata. It never executes a mod during validation.

## Limitation
Metadata formats and version ranges vary between mod loaders. This is a preflight check, not a complete dependency solver. Loader runtime remains authoritative.

## Verification
The project archive passes `unzip -t`. A Gradle compile was attempted, but the environment could not resolve `services.gradle.org`, so a successful Android build cannot be claimed here.
