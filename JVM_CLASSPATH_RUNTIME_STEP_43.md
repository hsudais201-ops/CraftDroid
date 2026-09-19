# CraftDroid Step 43 — JVM/ClassPath Runtime Hardening

## Fixed

- Added a deterministic Minecraft classpath resolver.
- Every resolved Mojang library artifact is checked for existence and non-zero size.
- Known artifact sizes are checked when supplied by the version manifest.
- Known SHA-1 hashes are checked before JVM startup.
- The Minecraft client JAR is checked the same way.
- Missing/corrupt artifacts now fail early with a clear diagnostic instead of becoming a later `ClassNotFoundException` or `NoClassDefFoundError`.
- Duplicate classpath paths are removed deterministically.
- Android GLFW/callback patch JARs remain ahead of Minecraft's desktop LWJGL artifacts.

## Why

A Java launcher cannot reliably boot Minecraft by simply adding whatever JARs happen to exist on disk. The version manifest defines the exact library artifacts, and Pojav-style launchers similarly depend on a complete runtime/JRE plus the appropriate LWJGL/GLFW components. The project now makes the classpath completeness requirement explicit before starting the embedded JVM.

## Verification

The source changes were inspected after extraction and the resulting ZIP was integrity-tested. A full Android/Gradle build remains dependent on the CI environment because the current local environment does not have a usable Gradle installation/distribution cache.
