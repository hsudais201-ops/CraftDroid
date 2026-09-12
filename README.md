# CraftDroid

Android Minecraft Java launcher project.

## Current state

- GitHub Actions Android build workflow: added
- CraftDroid Android source tree: included inside `CraftDroid_Launcher_2.4_GitHubActions_Step153.zip`
- The uploaded Step 153 archive contains the Gradle wrapper, `app/` module, Kotlin source, C++/GLFW bridge, resources, assets, tests, and build documentation.
- APK build: not yet verified on GitHub Actions
- Real Minecraft boot: not yet verified

## Next step

Extract/import the source tree from the Step 153 archive into the repository root so GitHub Actions can build the actual Android project directly.

## Target architecture

Android Surface -> GLFW -> LWJGL -> Minecraft
