# Step 178 — Droid Launcher Consolidation

## Goal

Droid Launcher is being consolidated into one maintainable Android project with feature parity targets inspired by current open-source Minecraft Java launchers, especially Zalith Launcher 2 and the PojavLauncher ecosystem.

## Repository audit

The current CraftDroid repository contains multiple CI workflows, repair/verification tooling, documentation, and the Step 153 launcher ZIP. The next implementation pass must recover the actual Android source from the available project artifacts before claiming the app is fully buildable.

## Feature-parity target

The target is practical feature parity, not a byte-for-byte copy: version management, game-directory configuration, renderer selection/plugin architecture, direct downloads for supported content, customizable launcher appearance, themes, account management, mod/resource-pack/shader/world management, Java/runtime management, diagnostics, and advanced touch controls.

Zalith Launcher 2 is GPL-3.0 and includes additional terms for modified distributions. Any source copied from GPL projects must remain license-compatible, retain required notices/terms, and keep Droid Launcher clearly distinguished from the original project. Prefer clean-room reimplementation or compatible dependencies when that is safer.

## Required assembly

1. Recover the best source from all available CraftDroid artifacts.
2. Create a single Android Gradle project under `app/`.
3. Consolidate duplicate launch/runtime implementations behind stable interfaces.
4. Integrate the existing artifact validation, classpath resolution, process monitoring, diagnostics, installation/repair, and world-management logic where the source is actually available.
5. Add the Droid Launcher UI and navigation shell.
6. Add the configurable touch-control system.
7. Configure GitHub Actions to install Gradle directly (target 9.6.0) so the build does not require a checked-in `gradle-wrapper.jar`.
8. Build tests and debug APK in CI.
9. Do not report success until a real CI build passes or the exact blocker is documented.
