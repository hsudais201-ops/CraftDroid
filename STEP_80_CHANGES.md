# Step 80 — JLI argv and runtime path correctness

- Fixed embedded `JLI_Launch` argument construction: the native bridge now always prepends the selected runtime's `bin/java` as `argv[0]` because the Kotlin command builder supplies arguments without an executable.
- Added explicit `aarch32` JRE library directories to the Java launch environment assembled by `LaunchCommandBuilder`, matching native JRE discovery.
- Kept the existing JLI/JVM preloading and native-stack logic unchanged.

## Verification
- Static source checks passed.
- ZIP integrity verified after packaging.
- Full Gradle/APK build remains environment-blocked when external Gradle distribution access is unavailable.
