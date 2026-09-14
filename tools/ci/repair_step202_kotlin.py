#!/usr/bin/env python3
"""Step 202 Kotlin compile repairs for the consolidated Droid Launcher source.

This intentionally patches the generated Step 177 WorldManager and the newer
performance tuner copied into the Step 200 build workspace.  The changes are
source-level and deterministic so the same repairs are applied in every CI run.
"""
from pathlib import Path
import sys


def patch_world_manager(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    original = text

    # java.io.File has no isSymbolicLink() member; java.nio.file.Files does.
    text = text.replace("!it.isSymbolicLink()", "!Files.isSymbolicLink(it.toPath())")
    text = text.replace("!world.isSymbolicLink()", "!Files.isSymbolicLink(world.toPath())")
    text = text.replace("!it.isSymbolicLink()", "!Files.isSymbolicLink(it.toPath())")

    # withWorldUnlocked is not inline, so `return` cannot exit the outer function
    # from inside its lambda.  Capture the result and return after the lock scope.
    old = '''    fun backupWorld(worldName: String): BackupInfo {
        val world = requireWorld(worldName)
        withWorldUnlocked(world) {
            val destinationDir = File(backupsDir, safeName(worldName)).apply { mkdirs() }
            check(destinationDir.isDirectory) { "Unable to create world backup directory" }
            val stamp = timestampFormat.format(Instant.now()).replace(":", "-")
            val finalFile = File(destinationDir, "${safeName(worldName)}-$stamp.zip")
            val tempFile = File(destinationDir, ".${finalFile.name}.tmp")
            if (tempFile.exists()) tempFile.delete()
            zipDirectory(world.toPath(), tempFile.toPath())
            moveAtomically(tempFile.toPath(), finalFile.toPath())
            return BackupInfo(safeName(worldName), finalFile, finalFile.lastModified(), finalFile.length())
        }
    }
'''
    new = '''    fun backupWorld(worldName: String): BackupInfo {
        val world = requireWorld(worldName)
        var result: BackupInfo? = null
        withWorldUnlocked(world) {
            val destinationDir = File(backupsDir, safeName(worldName)).apply { mkdirs() }
            check(destinationDir.isDirectory) { "Unable to create world backup directory" }
            val stamp = timestampFormat.format(Instant.now()).replace(":", "-")
            val finalFile = File(destinationDir, "${safeName(worldName)}-$stamp.zip")
            val tempFile = File(destinationDir, ".${finalFile.name}.tmp")
            if (tempFile.exists()) tempFile.delete()
            zipDirectory(world.toPath(), tempFile.toPath())
            moveAtomically(tempFile.toPath(), finalFile.toPath())
            result = BackupInfo(safeName(worldName), finalFile, finalFile.lastModified(), finalFile.length())
        }
        return requireNotNull(result)
    }
'''
    if old in text:
        text = text.replace(old, new)
    elif "return BackupInfo(safeName(worldName), finalFile" in text:
        raise SystemExit("WorldManager backupWorld has an unexpected shape; refusing unsafe rewrite")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def patch_performance_tuner(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    original = text
    old = '''            val (renderDistance, simulationDistance, graphics, particles, clouds, entityShadows) = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> listOf(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> listOf(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> listOf(14, 8, "fancy", "all", "true", "true")
            }
'''
    new = '''            data class TierSettings(
                val renderDistance: Int,
                val simulationDistance: Int,
                val graphics: String,
                val particles: String,
                val clouds: String,
                val entityShadows: String
            )
            val settings = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> TierSettings(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> TierSettings(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> TierSettings(14, 8, "fancy", "all", "true", "true")
            }
            val renderDistance = settings.renderDistance
            val simulationDistance = settings.simulationDistance
            val graphics = settings.graphics
            val particles = settings.particles
            val clouds = settings.clouds
            val entityShadows = settings.entityShadows
'''
    if old in text:
        text = text.replace(old, new)
    elif "val (renderDistance, simulationDistance, graphics, particles, clouds, entityShadows)" in text:
        raise SystemExit("Performance tuner destructuring has an unexpected shape; refusing unsafe rewrite")

    if text != original:
        path.write_text(text, encoding="utf-8")
        return 1
    return 0


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    world = root / "app/src/main/java/com/example/launcher/WorldManager.kt"
    tuner = root / "app/src/main/java/com/example/renderer/MinecraftPerformanceTuner.kt"
    if not world.is_file():
        raise SystemExit(f"Step 202: missing {world}")
    if not tuner.is_file():
        raise SystemExit(f"Step 202: missing {tuner}")

    world_changed = patch_world_manager(world)
    tuner_changed = patch_performance_tuner(tuner)
    print(f"[step202] WorldManager changed={world_changed}")
    print(f"[step202] MinecraftPerformanceTuner changed={tuner_changed}")
    print("[step202] Kotlin compile repairs complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
