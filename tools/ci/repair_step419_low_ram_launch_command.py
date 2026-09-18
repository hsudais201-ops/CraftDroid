#!/usr/bin/env python3
"""Step 419: enforce the device-safe heap at the real Minecraft JVM command boundary.

The generated launcher has two layers that can change JVM memory:
1. MinecraftLaunchManager creates LaunchConfig from launcher settings.
2. LaunchCommandBuilder serializes -Xms/-Xmx and later custom/version JVM arguments.

This repair makes the effective heap device-aware, keeps Xms small on constrained
devices, and prevents later -Xms/-Xmx arguments from overriding the safe values.
"""
from pathlib import Path
import sys

MANAGER = Path("app/src/main/java/com/example/launcher/MinecraftLaunchManager.kt")
BUILDER = Path("app/src/main/java/com/example/launcher/LaunchCommandBuilder.kt")

def patch_manager(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    old = """                val launchConfig = LaunchConfig(
                    versionDetail = versionDetail,
                    username = username,
                    uuid = uuid,
                    accessToken = accessToken,
                    isOfflineAccount = isOfflineAccount,
                    ramMb = ramMb,
                    customJvmArgs = customJvmArgs,
                    javaExecutable = javaRuntime.javaExecutable
                )
"""
    new = """                // Apply the same device-aware RAM policy used by SettingsRepository
                // immediately before constructing the real JVM launch configuration.
                // Keep the minimum heap deliberately small so low-RAM Android devices
                // do not reserve hundreds of megabytes before Minecraft is even ready.
                val effectiveRamMb = settingsRepository.getSafeRamMb(ramMb)
                val effectiveMinRamMb = minOf(512, maxOf(128, effectiveRamMb / 4))
                LauncherLogger.info(
                    "Effective Minecraft heap: Xms=${effectiveMinRamMb}M Xmx=${effectiveRamMb}M (requested=${ramMb}M)"
                )
                val launchConfig = LaunchConfig(
                    versionDetail = versionDetail,
                    username = username,
                    uuid = uuid,
                    accessToken = accessToken,
                    isOfflineAccount = isOfflineAccount,
                    ramMb = effectiveRamMb,
                    minRamMb = effectiveMinRamMb,
                    customJvmArgs = customJvmArgs,
                    javaExecutable = javaRuntime.javaExecutable
                )
"""
    if old not in s:
        if "val effectiveRamMb = settingsRepository.getSafeRamMb(ramMb)" in s:
            print("[step419] manager heap boundary already installed")
            return
        raise SystemExit("[step419] LaunchConfig anchor not found in MinecraftLaunchManager.kt")
    path.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("[step419] MinecraftLaunchManager now clamps real launch heap to device-safe settings")

def patch_builder(path: Path) -> None:
    s = path.read_text(encoding="utf-8")
    old = """        // 1. JVM Memory Arguments
        args.add("-Xms${config.minRamMb}M")
        args.add("-Xmx${config.ramMb}M")
"""
    new = """        // 1. JVM Memory Arguments
        // The manager has already applied the Android device-aware policy. Keep a
        // final hard safety ceiling here so direct builder callers cannot request
        // an accidentally enormous heap.
        val effectiveMaxRamMb = config.ramMb.coerceIn(128, 4096)
        val effectiveMinRamMb = config.minRamMb.coerceIn(128, effectiveMaxRamMb)
        args.add("-Xms${effectiveMinRamMb}M")
        args.add("-Xmx${effectiveMaxRamMb}M")
"""
    if old in s:
        s = s.replace(old, new, 1)
    elif "val effectiveMaxRamMb = config.ramMb.coerceIn(128, 4096)" not in s:
        raise SystemExit("[step419] JVM memory argument anchor not found in LaunchCommandBuilder.kt")

    helper = """    private fun isHeapArgument(argument: String): Boolean =
        argument.startsWith("-Xmx", ignoreCase = true) ||
            argument.startsWith("-Xms", ignoreCase = true)

"""
    anchor = """    fun buildCommand(config: LaunchConfig"""
    if "private fun isHeapArgument(argument: String)" not in s:
        pos = s.find(anchor)
        if pos < 0:
            raise SystemExit("[step419] buildCommand declaration not found")
        s = s[:pos] + helper + s[pos:]

    old_custom = """                if (isValidJvmArg(token)) {
                    args.add(token)
                } else {
"""
    new_custom = """                if (isValidJvmArg(token) && !isHeapArgument(token)) {
                    args.add(token)
                } else {
"""
    if old_custom in s:
        s = s.replace(old_custom, new_custom, 1)
    elif "isValidJvmArg(token) && !isHeapArgument(token)" not in s:
        raise SystemExit("[step419] custom JVM argument filter anchor not found")

    old_version = """            val resolved = resolveArgumentItem(item, templateMap)
            args.addAll(resolved)
"""
    new_version = """            val resolved = resolveArgumentItem(item, templateMap)
            args.addAll(resolved.filterNot(::isHeapArgument))
"""
    if old_version in s:
        s = s.replace(old_version, new_version, 1)
    elif "args.addAll(resolved.filterNot(::isHeapArgument))" not in s:
        raise SystemExit("[step419] version JVM argument filter anchor not found")

    path.write_text(s, encoding="utf-8")
    print("[step419] LaunchCommandBuilder now enforces final Xms/Xmx safety and strips later heap overrides")

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    manager = root / MANAGER
    builder = root / BUILDER
    if not manager.is_file() or not builder.is_file():
        raise SystemExit("[step419] generated launch manager/builder sources are missing")
    patch_manager(manager)
    patch_builder(builder)

    manager_text = manager.read_text(encoding="utf-8")
    builder_text = builder.read_text(encoding="utf-8")
    required = [
        (manager_text, "settingsRepository.getSafeRamMb(ramMb)"),
        (manager_text, "minRamMb = effectiveMinRamMb"),
        (manager_text, "Effective Minecraft heap"),
        (builder_text, "val effectiveMaxRamMb = config.ramMb.coerceIn(128, 4096)"),
        (builder_text, "private fun isHeapArgument(argument: String)"),
        (builder_text, "isValidJvmArg(token) && !isHeapArgument(token)"),
        (builder_text, "args.addAll(resolved.filterNot(::isHeapArgument))"),
    ]
    for text, needle in required:
        if needle not in text:
            raise SystemExit(f"[step419] missing final contract: {needle}")
    print("[step419] final low-RAM launch heap contract verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())