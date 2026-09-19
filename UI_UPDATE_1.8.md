# CraftDroid 1.8 UI/UX Update

## Changed directly in the project

- `HomeScreen.kt`: refreshed launcher dashboard, clearer hierarchy, status/health card, account strip, performance cards and touch-controls shortcut.
- `Theme.kt`: consolidated dark-first gaming typography and palette.
- `Color.kt`: added elevated surface and success colors.
- `MainActivity.kt`: polished bottom navigation surface and elevation.

## Important technical distinction

The new launcher status card reports configuration state only. It does not report the Minecraft renderer as verified merely because the APK builds. Rendering still requires an actual Android/ChromeOS launch test.

## Build target

The project remains on Android Gradle Plugin 9.4.0 / Gradle 9.6.0 / JDK 17 compatible configuration. Android's current AGP 9.4 compatibility documentation lists Gradle 9.6.0 and JDK 17 for AGP 9.4.
