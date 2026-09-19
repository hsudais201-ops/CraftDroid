# CraftDroid Step 52 — Renderer ELF dependency validation

The renderer/native stack now performs a lightweight ELF `DT_NEEDED` scan before the Android loader is asked to resolve the complete stack.

## What changed

- `NativeDependencyVerifier` parses 32-bit and 64-bit little-endian ELF program headers.
- It reads `PT_DYNAMIC`, `DT_STRTAB`, and `DT_NEEDED` entries.
- Each dependency is checked against the same extracted renderer directory.
- Common Android system libraries are treated as platform-provided and do not need to be bundled.
- Missing bundled dependencies are reported with the owning library, for example `libfoo.so -> libbar.so`.
- `NativeComponentManager` refuses to declare a native stack ready if unresolved dependencies remain.
- `NativeGameBridge.loadNativeStack()` repeats the check immediately after the actual native load/validation pass.

This catches a class of failures where the main `.so` exists and has the correct ABI, but one of its transitive dependencies is absent.
