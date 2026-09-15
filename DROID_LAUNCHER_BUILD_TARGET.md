# Droid Launcher build target

The acceptance target is a functional Android Minecraft: Java Edition launcher with a polished UI and practical feature parity with modern open-source Android launchers.

It is not a promise of literal 100% equivalence to any other launcher: runtime support depends on Android device, Minecraft version, Java runtime, renderer, native libraries, and licensing constraints. The goal is to close functional gaps systematically and verify each capability with tests or runtime checks.

## Core target

- One Android application branded Droid Launcher.
- Minecraft version installation and management.
- Java runtime management.
- Libraries, assets, client JAR and native handling.
- Correct launch classpath construction.
- Accounts and profiles.
- Separate game instances and directories.
- Fabric, Forge and compatible mod-loader workflows where supported.
- Mods, resource packs, shaders and worlds.
- Backups, import/export and repair.
- Launch diagnostics and crash recovery.
- Process monitoring.
- Renderer selection where supported by the runtime.
- Fully customizable Android touch controls.
- Landscape-first polished launcher UI with themes and configurable appearance.
- GitHub Actions APK builds without depending on a checked-in gradle-wrapper.jar.
