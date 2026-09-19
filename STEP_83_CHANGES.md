# CraftDroid Step 83

## Native LWJGL load-order hardening

Fixed a subtle Step 82 issue where the alternate LWJGL JNI family was removed only after the generic dependency scan. Because native libraries are loaded globally, that was too late: an alternate `liblwjgl.so`/`liblwjgl3.so` could already have been loaded.

The alternate LWJGL JNI family is now excluded **before** any dependency scan or `RTLD_GLOBAL` load. The selected LWJGL family remains the only LWJGL JNI implementation allowed into the process.

This reduces JNI_OnLoad and symbol-resolution collisions when native packs contain both LWJGL generations.
