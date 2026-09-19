# CraftDroid Step 44 — Java Runtime Compatibility Hardening

## Fixed

- Runtime selection no longer chooses an arbitrary newer Java release.
- Java 8 requests select only Java 8.
- Java 17 requests select only Java 17.
- Java 21 requests select only Java 21.
- Java 25 requests select only Java 25.
- Minecraft Java 16 requests use the bundled Android Java 17 runtime and install Java 17 when necessary.
- Unsupported Java requirements fail before JVM startup with a clear error.
- `java -version` is now parsed and recorded as the detected runtime major.
- The launch pipeline performs a final requested-vs-installed Java compatibility gate immediately before constructing the Minecraft launch command.

## Why

A previous `>= requiredJava` fallback could silently select Java 21 or Java 25 for a game that requested Java 17. That makes debugging native/JVM crashes much harder and can introduce compatibility changes that are unrelated to the Minecraft installation itself.

Pojav-style Android launchers explicitly ship mobile OpenJDK runtimes for multiple Java generations and select the appropriate runtime for the Minecraft version. The project documentation lists Android OpenJDK 8, 17, and 21 runtimes and separate LWJGL compatibility paths. See the PojavLauncher project documentation for the reference architecture.

## Verification status

Static source checks completed successfully for this step. A full Android APK build is still dependent on the project's GitHub CI environment because the current local environment does not contain a usable Gradle distribution/network path.
