# Build CraftDroid in a browser

The project includes `.github/workflows/build-apk.yml` so it can be built with
GitHub Actions without installing Android Studio on the Chromebook/phone.

## Steps

1. Create a GitHub repository.
2. Upload the contents of this ZIP to the repository.
3. Commit the files to `main`.
4. Open **Actions** → **Build CraftDroid APK**.
5. Press **Run workflow**.
6. Wait for tests and the debug/release builds to finish.
7. Open the completed workflow run and download `CraftDroid-debug-apk`.

The current workflow uses Android Gradle Plugin 9.4.0, which requires Gradle
9.6.0 and JDK 17, matching the project configuration.

## Important

The APK is installable, but Minecraft Java itself needs Android-specific native
components. The launcher now has a real OpenJDK 17/21 downloader, but it does
not yet bundle the complete Android LWJGL/GLFW + renderer stack. See
`BUILD_REVIEW.md` before treating a successful APK build as proof that a
particular Minecraft version can boot.
