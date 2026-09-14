#!/usr/bin/env python3
"""Step 225: bind the selected installed Minecraft artifact paths to launch."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step225] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def method_end(s: str, start: int) -> int:
    vals = [s.find('\n    private fun ', start + 1), s.find('\n    companion object', start + 1)]
    vals = [v for v in vals if v >= 0]
    if not vals:
        raise SystemExit('[step225] could not find launch method end')
    return min(vals)


def ensure_helper(path_file: Path) -> None:
    if path_file.exists():
        return
    path_file.write_text('''package com.example.launcher

import android.content.Context
import java.io.File

/** Resolved filesystem locations for one installed Minecraft version. */
object MinecraftLaunchPaths {
    data class Result(
        val version: String,
        val minecraftRoot: File,
        val versionDir: File,
        val clientJar: File,
        val librariesDir: File,
        val assetsDir: File,
        val nativesDir: File,
        val valid: Boolean,
        val error: String? = null
    )

    fun resolve(context: Context, version: String): Result {
        val root = MinecraftStorageResolver.root(context)
        val versionDir = MinecraftStorageResolver.version(context, version)
        val client = File(versionDir, "$version.jar")
        val libraries = MinecraftStorageResolver.libraries(context)
        val assets = MinecraftStorageResolver.assets(context)
        val natives = MinecraftStorageResolver.natives(context, version)
        return when {
            version.isBlank() -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft version is empty")
            !File(versionDir, "$version.json").isFile -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Version metadata is missing")
            !client.isFile || client.length() <= 0L -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft client JAR is missing")
            !libraries.isDirectory -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft libraries directory is missing")
            !assets.isDirectory -> Result(version, root, versionDir, client, libraries, assets, natives, false, "Minecraft assets directory is missing")
            else -> Result(version, root, versionDir, client, libraries, assets, natives, true)
        }
    }
}
''', encoding='utf-8')


def patch_method(s: str, signature: str) -> str:
    start = s.find(signature)
    if start < 0:
        return s
    end = method_end(s, start)
    block = s[start:end]
    if 'MinecraftLaunchPaths.resolve(this, version)' not in block:
        profile = '        val profile = selectedMinecraftProfile()\n'
        version = '        val version = selectedMinecraftVersion()\n'
        injection = '''        val launchPaths = MinecraftLaunchPaths.resolve(this, version)
        if (!launchPaths.valid) {
            Toast.makeText(this, "Minecraft $version is not launch-ready: ${launchPaths.error ?: "unknown artifact error"}", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
'''
        if version in block:
            block = block.replace(version, version + injection, 1)
        elif profile in block:
            # The generated lower-level server launch path can have profile but no local version.
            prefix = '        val version = selectedMinecraftVersion()\n'
            block = block.replace(profile, profile + prefix + injection, 1)
        else:
            return s
    extras_anchor = '            intent.putExtra("minecraft_java", resolvedJava)\n'
    extras = extras_anchor + '''            intent.putExtra("minecraft_root", launchPaths.minecraftRoot.absolutePath)
            intent.putExtra("minecraft_version_dir", launchPaths.versionDir.absolutePath)
            intent.putExtra("minecraft_client_jar", launchPaths.clientJar.absolutePath)
            intent.putExtra("minecraft_libraries_dir", launchPaths.librariesDir.absolutePath)
            intent.putExtra("minecraft_assets_dir", launchPaths.assetsDir.absolutePath)
            intent.putExtra("minecraft_natives_dir", launchPaths.nativesDir.absolutePath)
'''
    if 'intent.putExtra("minecraft_client_jar", launchPaths.clientJar.absolutePath)' not in block and extras_anchor in block:
        block = block.replace(extras_anchor, extras, 1)
    return s[:start] + block + s[end:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    source_root = root / "app/src/main/java"
    src = root / "app/src/main/java/com/example/launcher"
    ui = find_one(source_root, "DroidLauncherUiActivity.kt")
    manager = find_one(source_root, "MinecraftLaunchManager.kt")
    path_file = src / "MinecraftLaunchPaths.kt"
    ensure_helper(path_file)

    s = ui.read_text(encoding="utf-8")
    original = s
    for signature in (
        '    private fun launchSelectedMinecraft() {',
        '    private fun launchExistingActivityWithServer() {',
    ):
        s = patch_method(s, signature)
        if s != original:
            break
    ui.write_text(s, encoding="utf-8")

    m = manager.read_text(encoding="utf-8")
    marker = '// Step 225 launch-path contract: explicit filesystem paths are passed to the game activity.\nprivate const val DROID_LAUNCH_PATHS_VERSION = "225"\n'
    if 'DROID_LAUNCH_PATHS_VERSION' not in m:
        manager.write_text(marker + m, encoding="utf-8")
        m = marker + m

    combined = s + '\n' + m + '\n' + path_file.read_text(encoding='utf-8')
    for needle in ('MinecraftStorageResolver.version(context, version)', 'MinecraftStorageResolver.libraries(context)', 'MinecraftStorageResolver.assets(context)', 'MinecraftStorageResolver.natives(context, version)', 'minecraft_client_jar', 'DROID_LAUNCH_PATHS_VERSION'):
        if needle not in combined:
            raise SystemExit(f'[step225] missing launch-path contract: {needle}')

    print('[step225] installed Minecraft filesystem paths resolved before launch')
    print('[step225] explicit client/library/assets/native paths added to launch intent')
    print('[step225] canonical MinecraftStorageResolver contract installed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
