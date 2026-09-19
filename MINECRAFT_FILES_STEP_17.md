# CraftDroid Step 17 — Minecraft Filesystem & Asset Integrity

## Goal
Make the launcher fail early on incomplete/corrupt Minecraft installations instead of allowing missing libraries/assets to become confusing JVM or renderer crashes.

## Added
- `GameInstallationVerifier` validates the selected client JAR against its manifest SHA-1 and size.
- Validates the asset index and every referenced asset object.
- Validates downloaded library artifacts and native archives.
- Checks that versions declaring native dependencies have extracted `.so` files.
- Produces concise launcher diagnostics and logs the first integrity failures.
- Runs before Java/OpenJDK startup.

## Storage layout
The verifier uses the existing Minecraft layout:
- `versions/<id>/<id>.json`
- `versions/<id>/<id>.jar`
- `versions/<id>/natives/`
- `libraries/<maven-path>`
- `assets/indexes/<index>.json`
- `assets/objects/<first-two-hash-chars>/<hash>`

## Repair behavior
This step intentionally does not silently redownload files. It reports exactly what is missing/corrupt so the installer/repair flow can redownload the affected artifacts.

## Compatibility
Minecraft version manifests describe the Java libraries, launch arguments and assets required for a version. Pojav's downloader similarly downloads the asset index, asset objects, client JAR and libraries before launch. citeturn0search7turn0search0

## Remaining limitation
Version inheritance/custom-loader merging is not yet a full recursive manifest resolver. The verifier validates the resolved `VersionDetail` that CraftDroid currently parses. Forge/Fabric-specific installer processing remains a later step.
