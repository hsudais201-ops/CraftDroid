# CraftDroid third-party runtime notices

CraftDroid can download Android OpenJDK 17/21 runtime archives from the public
`AngelAuraMC/angelauramc-openjdk-build` release mirror. The mirror describes
these releases as a download center for Amethyst JREs.

The launcher verifies the published SHA-256 values for the pinned Java 17/21
ARM/ARM64/x86_64 packages where a complete digest is available. Java 21/x86 is
left without a pinned digest because the public release page currently exposes
an incomplete digest for that asset; the launcher therefore does not claim a
cryptographic verification for that package.

OpenJDK licensing and attribution remain the responsibility of the runtime
distributor. CraftDroid does not bundle OpenJDK into the APK.

## Archive libraries

- Apache Commons Compress 1.28.0 — Apache License 2.0.
- XZ for Java 1.12 — 0BSD.

These libraries are used only to unpack Android JRE `.tar.xz` packages.

## Android GLFW stub

CraftDroid downloads the PojavLauncher Android GLFW Java stub at runtime rather
than embedding the upstream jar in the APK. PojavLauncher documents the
`jre_lwjgl3glfw` module as its custom GLFW stub for Minecraft 1.13+.
The relevant upstream projects use LWJGL3's BSD-3-Clause licensing and GLFW's
zlib licensing; retain the upstream notices when redistributing the downloaded
component.
