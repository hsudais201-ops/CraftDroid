# CraftDroid Step 25 — Forge/NeoForge Processor Pipeline

Added a client-side Forge/NeoForge post-processing pipeline.

## What changed
- Reads `install_profile.json` processor definitions.
- Resolves client-side `{TOKEN}` values including `SIDE`, `MINECRAFT_JAR`, `MINECRAFT_VERSION`, `ROOT`, `LIBRARY_DIR`, and `INSTALLER`.
- Resolves `[maven:group:artifact:version[:classifier]]` processor arguments.
- Extracts installer-embedded `maven/...` libraries before falling back to downloads.
- Uses the selected CraftDroid Java runtime to execute processor JARs.
- Reads each processor JAR's `Main-Class` from its manifest.
- Builds the processor classpath and runs processors in declared order.
- Skips processors whose declared outputs already exist with the expected SHA-1.
- Verifies declared outputs after every processor.
- Rejects non-zero processor exit codes and missing dependencies.
- Restricts embedded data extraction to the CraftDroid installer-data directory.

This implements the core processor contract used by modern Forge/NeoForge installers. It does **not** claim that every historical Forge installer schema is supported; legacy/V1 variants still require separate handling.
