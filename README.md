# CraftDroid

Android Minecraft Java launcher project.

## Current state

- GitHub Actions Android build workflow: added
- Actual CraftDroid Android source tree: not yet imported
- APK build: blocked until the Android source tree and Gradle wrapper are present
- Real Minecraft boot verification: not yet possible until the runnable project is imported

## Required next import

The Step 153 archive available in this project contains only the CI workflow and documentation; it does not contain the launcher source. The real CraftDroid project ZIP/source tree must be imported before CI can produce an APK.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
