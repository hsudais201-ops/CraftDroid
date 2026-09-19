# CraftDroid real Minecraft runtime

This release prepares the missing runtime pieces needed for real Minecraft Java boot:

- Android OpenJDK 17/21/25 downloaded on demand and SHA-256 verified.
- Minecraft client, libraries, asset index and asset objects downloaded from Mojang metadata.
- Native Android renderer stack downloaded on demand for the device ABI.
- Renderer environment variables aligned with Pojav/Amethyst conventions.
- Renderer libraries loaded before the embedded JVM.
- JVM core libraries preloaded before JLI_Launch.
- Minecraft launch waits for the Android GameSurface instead of racing the Activity creation.
- Renderer native directory is included in java.library.path and LD_LIBRARY_PATH.

Java 25 is required by Minecraft 26.1+. Older Minecraft releases continue to use their version metadata Java requirement.

A real device test is still required because GPU driver behavior differs between Android devices.


The launcher intentionally does not bundle proprietary Minecraft game files. The player installs a Minecraft version through Mojang's version metadata and supplies the account/license required by Mojang.
