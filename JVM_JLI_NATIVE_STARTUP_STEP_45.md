# CraftDroid Step 45 — JVM/JLI Native Startup Hardening

This step hardens the boundary between the Android process and the bundled Android OpenJDK.

## Changes

- Corrected the native `JLI_Launch` function-pointer signature to match OpenJDK's launcher API (`const char**` for Java arguments/classpath vectors and JNI boolean types for the final flags).
- Validates `lib/jli/libjli.so` and finds an actual `libjvm.so` before invoking JLI.
- Establishes `JAVA_HOME`, `JLI_HOME`, and the JRE library search path in native code before any JRE library is opened.
- Uses absolute JRE paths for preload attempts so desktop/renderer libraries cannot accidentally satisfy generic JVM library names.
- Loads only JRE libraries that are actually present and logs optional preload failures without making unrelated modules mandatory.
- Ensures `libjvm.so` is resident before JLI starts, avoiding a second accidental copy when possible.
- Normalizes `argv[0]` to the selected runtime's `bin/java` when the Java launcher argument is omitted or is only the placeholder `java`.
- Adds explicit native return codes for missing `libjli.so` and `libjvm.so`.
- Keeps the existing embedded-JVM stdout/stderr capture and clean-stop behavior.

## Verification status

The project source and archive structure were checked after modification. A full Android/NDK build is still environment-dependent because the current execution environment does not have a working local Gradle distribution/network access to fetch it.

The JLI signature is aligned with the OpenJDK `JLI_Launch` declaration. citeturn932146search0turn932146search8
