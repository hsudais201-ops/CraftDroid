# CraftDroid Step 24 — Forge/NeoForge Bootstrap

Adds `ForgeNeoForgeInstaller` for Forge and NeoForge installer JAR handling.

## Added
- Downloads the official Forge/NeoForge installer JAR from Maven.
- Inspects the installer without executing arbitrary desktop installer code.
- Reads embedded `install_profile.json` / `version.json` metadata when available.
- Creates an isolated loader version profile and reuses the installed vanilla client JAR.
- Downloads libraries explicitly described by the embedded profile.
- Detects whether installer processors are still required.
- Exposes the installer through `LauncherContainer`.

## Important limitation
Forge/NeoForge installers can contain processors that transform Minecraft files and generate final launch metadata. This step intentionally does **not** execute those processors inside Android. A later step must implement a controlled processor/runtime pipeline before claiming full Forge/NeoForge installation.

NeoForge's documentation recommends separate custom profiles for modded instances, and Forge's installer likewise prepares a version/profile plus libraries. See official documentation for the respective installer workflows.
