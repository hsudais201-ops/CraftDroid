# CraftDroid Step 95

## Embedded JVM environment restoration fix

Fixed a real ordering bug in `nativeLaunchJava()`:

- `ScopedEnvironment` now snapshots the caller's environment **before** CraftDroid applies launch overrides.
- `JAVA_HOME`, `JLI_HOME`, `LD_LIBRARY_PATH`, and all explicitly supplied environment keys are therefore restored to their pre-launch values when `JLI_Launch()` returns or launch setup fails.
- This prevents one Minecraft launch from permanently changing the process environment used by subsequent launcher operations.
