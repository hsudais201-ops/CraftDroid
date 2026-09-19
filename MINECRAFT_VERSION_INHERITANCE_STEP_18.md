# CraftDroid Runtime Step 18 — Minecraft Version Inheritance

## What changed
CraftDroid now resolves `inheritsFrom` version profiles before installation and launch.

### Resolution behavior
- Loads the parent version JSON from local `.minecraft/versions/<id>/<id>.json` when available.
- If the parent is not installed and it is an official Mojang version, resolves its metadata through Mojang's official version manifest.
- Recursively resolves parent chains.
- Detects circular inheritance.
- Merges parent + child libraries by Maven coordinate, with the child definition winning.
- Merges modern `arguments.jvm` and `arguments.game` arrays in parent-first order.
- Allows child metadata/downloads/assets/mainClass fields to override inherited values.
- Supports legacy `minecraftArguments` profiles.
- Removes `inheritsFrom` after normalization so downstream launch code receives one complete manifest.

## Why this matters
Mod-loader profiles such as Fabric/Forge can use a child profile that inherits the base Minecraft profile. Without resolving the chain, the launcher can miss required libraries, assets, arguments, or the correct Java requirement and fail later during JVM startup.

## Safety
Only JSON metadata is merged. The resolver does not execute installer code or processor jars. It also fails closed on missing parents or circular inheritance.
