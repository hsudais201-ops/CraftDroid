# Step 26 — Forge/NeoForge Installer Compatibility Hardening

CraftDroid now detects multiple Forge/NeoForge installer layouts instead of assuming a single modern processor format.

## Added
- Installer format detection for:
  - V1 `install_profile.json` + `versionInfo`
  - V2 `install_profile.json` + `version.json`
  - profile-only legacy `install_profile.json`
  - `version.json`-only layouts
- Normalized profile loading for bootstrap and processor execution.
- Merged loader libraries from installer and embedded version metadata.
- Merged processor metadata when processors live under `versionInfo`.
- Explicit rejection of installers that contain neither supported profile file.
- Existing processor execution continues to honor client-side processors, token expansion, output hashes, and declared classpaths.

## Compatibility boundary
Forge's own documentation notes substantial differences across historical Minecraft/Forge versions. This step broadens support for profile-based legacy and modern installers, but it does not claim support for every pre-profile/old jar-mod installer format. Unsupported installers now fail early with a specific reason instead of failing later during launch.

NeoForge current installers are profile/processor based, so the normalized path also covers the current NeoForge model.

## Verification
The project archive is checked for ZIP integrity. A full Android Gradle build remains dependent on access to the configured Gradle distribution/services in the build environment.
