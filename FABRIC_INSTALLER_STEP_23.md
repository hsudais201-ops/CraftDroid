# CraftDroid Step 23 — Fabric Loader Installation

Implemented a real Fabric profile installation path using Fabric Meta's standard launcher profile endpoint.

## Added
- `FabricLoaderInstaller.kt`
- Fetches the selected Fabric loader profile JSON.
- Verifies that the profile inherits from the requested Minecraft version.
- Writes the generated profile under `versions/<fabric-profile-id>/`.
- Copies the vanilla client JAR into the generated profile because CraftDroid's launch preflight requires a local profile JAR.
- Reuses the extracted Android native `.so` files from the vanilla profile.
- Downloads Fabric-declared Maven libraries with optional SHA-1/size verification.
- Supports both flat `libraries` metadata and nested `launcherMeta.libraries` metadata.
- Added Fabric repository URL handling to `VersionJsonParser` fallback Maven resolution.
- Exposed the installer from `LauncherContainer`.

Fabric's official Meta API provides `/v2/versions/loader/<game>/<loader>/profile/json`, and its profile is intended for standard Minecraft launcher installation. The generated profile uses the Fabric loader main class and inherits the selected Minecraft version.

## Limitation
This step implements Fabric installation. Forge/NeoForge installer processing remains a separate step because their installer formats and generated profiles are different.
