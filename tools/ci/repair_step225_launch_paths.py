#!/usr/bin/env python3
"""Step 225: bind the selected installed Minecraft artifact paths to launch.

Runs after the Step 224 preflight repair against the generated launcher source.
It adds a small, dependency-light launch-path contract and passes the resolved
version directory/client JAR/library root through the existing launch intent.
"""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step225] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    manager = find_one(root / "app/src/main/java", "MinecraftLaunchManager.kt")

    helper = r'''package com.example.launcher

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
        val root = File(context.filesDir, "minecraft")
        val versionDir = File(root, "versions/$version")
        val client = File(versionDir, "$version.jar")
        val libraries = File(root, "libraries")
        val assets = File(root, "assets")
        val natives = File(root, "versions/$version/natives")
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
'''
    path_file = src / "MinecraftLaunchPaths.kt"
    if not path_file.exists():
        path_file.write_text(helper, encoding="utf-8")

    s = ui.read_text(encoding="utf-8")
    marker = '        val version = selectedMinecraftVersion()\n'
    if 'MinecraftLaunchPaths.resolve(this, version)' not in s:
        replacement = marker + '''        val launchPaths = MinecraftLaunchPaths.resolve(this, version)
        if (!launchPaths.valid) {
            Toast.makeText(this, "Minecraft $version is not launch-ready: ${launchPaths.error ?: "unknown artifact error"}", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
'''
        # Only patch launchSelectedMinecraft's first version declaration.
        start = s.find('    private fun launchSelectedMinecraft() {')
        if start < 0:
            raise SystemExit('[step225] launchSelectedMinecraft not found')
        pos = s.find(marker, start)
        if pos < 0:
            raise SystemExit('[step225] launchSelectedMinecraft version anchor not found')
        s = s[:pos] + s[pos:].replace(marker, replacement, 1)

    # Add paths to the existing launch intent when server launch is used.
    extras_anchor = '            intent.putExtra("minecraft_java", resolvedJava)\n'
    extras = extras_anchor + '''            intent.putExtra("minecraft_root", launchPaths.minecraftRoot.absolutePath)
            intent.putExtra("minecraft_version_dir", launchPaths.versionDir.absolutePath)
            intent.putExtra("minecraft_client_jar", launchPaths.clientJar.absolutePath)
            intent.putExtra("minecraft_libraries_dir", launchPaths.librariesDir.absolutePath)
            intent.putExtra("minecraft_assets_dir", launchPaths.assetsDir.absolutePath)
            intent.putExtra("minecraft_natives_dir", launchPaths.nativesDir.absolutePath)
'''
    if 'intent.putExtra("minecraft_client_jar", launchPaths.clientJar.absolutePath)' not in s:
        if extras_anchor in s:
            # Path variables may not exist in this different launch method; add a local resolver there.
            launch_start = s.find('    private fun launchExistingActivityWithServer() {')
            if launch_start >= 0:
                launch_end = s.find('\n    private fun getLastLaunchState()', launch_start)
                block = s[launch_start:launch_end if launch_end >= 0 else len(s)]
                if 'val launchPaths = MinecraftLaunchPaths.resolve(this, selectedVersion)' not in block:
                    anchor = '        val resolvedJava = getResolvedJavaForLaunch(selectedVersion)\n'
                    if anchor in block:
                        block = block.replace(anchor, anchor + '        val launchPaths = MinecraftLaunchPaths.resolve(this, selectedVersion)\n', 1)
                    else:
                        raise SystemExit('[step225] selected launch Java anchor not found')
                block = block.replace(extras_anchor, extras, 1)
                s = s[:launch_start] + block + s[launch_end if launch_end >= 0 else len(s):]

    ui.write_text(s, encoding="utf-8")

    # Add manager-side diagnostics without making assumptions about its full implementation.
    m = manager.read_text(encoding="utf-8")
    contract = '''\n// Step 225 launch-path contract: the Android launcher supplies explicit\n// minecraft_root/version_dir/client_jar/libraries/assets/natives paths.\nprivate const val DROID_LAUNCH_PATHS_VERSION = "225"\n'''
    if 'DROID_LAUNCH_PATHS_VERSION' not in m:
        m = contract + m
        manager.write_text(m, encoding="utf-8")

    for needle in (
        'MinecraftLaunchPaths.resolve(this, version)',
        'minecraft_client_jar',
        'minecraft_libraries_dir',
        'minecraft_assets_dir',
        'minecraft_natives_dir',
        'DROID_LAUNCH_PATHS_VERSION',
    ):
        if needle not in (s + m):
            raise SystemExit(f"[step225] missing launch-path contract: {needle}")

    print('[step225] installed Minecraft filesystem paths resolved before launch')
    print('[step225] explicit client/library/assets/native paths added to launch intent')
    print('[step225] manager launch-path contract marker added')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
