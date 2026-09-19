# Step 79 – Android JRE layout and embedded JLI startup hardening

- Added Pojav/Android `aarch32` runtime layouts, including `aarch32/jli` and `aarch32/client`, matching observed Android OpenJDK packaging.
- Added `client`/`server` subdirectories for all supported ABI layouts when present.
- Expanded `libjvm.so` discovery to cover ABI-specific client/server locations.
- Expanded optional JRE preload coverage to the libraries commonly loaded by Pojav Android OpenJDK runtimes.
- Kept the preload operations optional: the selected `libjvm.so` and `libjli.so` remain the hard launch gates.

Reference behavior: Pojav logs show Android runtimes such as `lib/aarch32/jli/libjli.so` and `lib/aarch32/client/libjvm.so`, followed by JLI startup. OpenJDK's JLI launcher then loads the VM through `dlopen` and resolves the JNI invocation functions. Sources: PojavLauncher issue logs and OpenJDK launcher source.
