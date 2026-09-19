# Step 78 — Android JRE/JLI Runtime Layout Hardening

- Java runtime validation now accepts both standard and ABI-specific Android OpenJDK layouts for `libjli.so` and `libjvm.so`.
- `java -version` is launched with the discovered JRE library directories in `LD_LIBRARY_PATH`.
- `JAVA_HOME` and the real discovered `JLI_HOME` are set during runtime validation.
- Native JLI launch now sets `JLI_HOME` to the directory containing the actual discovered `libjli.so`, rather than assuming `lib/jli`.
- This keeps Java 8/17/21/25 startup consistent across ARM, ARM64, x86, and x86_64 package layouts.
