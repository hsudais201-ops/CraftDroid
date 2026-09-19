# CraftDroid Step 93

## Native ABI admission hardening

- GLFW/LWJGL family identity is checked **before** `dlopen()`.
- An incompatible `libglfw.so`/`libglfw3.so` or `liblwjgl.so`/`liblwjgl3.so` is rejected before it can enter the process-global linker namespace.
- The accepted exact handle/name is then recorded for later validation and lifecycle reuse.
- This closes the remaining gap where Step 92 could reject an ABI switch only after the alternate library had already been loaded.
