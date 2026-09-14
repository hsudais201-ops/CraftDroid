#!/usr/bin/env python3
"""Step 225: bind selected installed Minecraft filesystem paths to launch."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step225] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def repair_manager_import_order(manager: Path) -> None:
    s = manager.read_text(encoding="utf-8")
    marker = '// Step 225 launch-path contract: explicit filesystem paths are passed to the game activity.\n'
    const = 'private const val DROID_LAUNCH_PATHS_VERSION = "225"\n'
    s = s.replace(marker + const, "")
    # Remove any previous duplicate constant; it will be restored after imports.
    s = s.replace(const, "")
    lines = s.splitlines(keepends=True)
    package_i = next((i for i, x in enumerate(lines) if x.startswith("package ")), None)
    if package_i is None:
        raise SystemExit("[step225] manager package declaration not found")
    import_end = package_i + 1
    while import_end < len(lines) and (lines[import_end].startswith("import ") or not lines[import_end].strip()):
        import_end += 1
    head = ''.join(lines[:import_end]).rstrip('\n') + '\n\n'
    tail = ''.join(lines[import_end:]).lstrip('\n')
    manager.write_text(head + marker + const + tail, encoding="utf-8")


def patch_ui(ui: Path) -> None:
    s = ui.read_text(encoding="utf-8")
    if 'import android.widget.Toast' not in s:
        s = s.replace('import android.widget.', 'import android.widget.Toast\nimport android.widget.', 1) if 'import android.widget.' in s else s

    # The generated UI has changed shape several times. Add the path gate directly
    # to the concrete launch method instead of depending on a fragile extras anchor.
    sig = '    private fun launchExistingActivityWithServer() {'
    start = s.find(sig)
    if start >= 0:
        next_sig = s.find('\n    private fun ', start + len(sig))
        end = next_sig if next_sig >= 0 else len(s)
        block = s[start:end]
        if 'val launchPaths = MinecraftLaunchPaths.resolve(this, version)' not in block:
            version_line = '        val version = selectedMinecraftVersion()\n'
            gate = '''        val launchPaths = MinecraftLaunchPaths.resolve(this, version)
        if (!launchPaths.valid) {
            Toast.makeText(this, "Minecraft $version is not launch-ready: ${launchPaths.error ?: "unknown artifact error"}", Toast.LENGTH_LONG).show()
            return
        }
'''
            if version_line in block:
                block = block.replace(version_line, version_line + gate, 1)
            else:
                block = block.replace(sig + '\n', sig + '\n' + version_line + gate, 1)
        extras = '''        intent.putExtra("minecraft_root", launchPaths.minecraftRoot.absolutePath)
        intent.putExtra("minecraft_version_dir", launchPaths.versionDir.absolutePath)
        intent.putExtra("minecraft_client_jar", launchPaths.clientJar.absolutePath)
        intent.putExtra("minecraft_libraries_dir", launchPaths.librariesDir.absolutePath)
        intent.putExtra("minecraft_assets_dir", launchPaths.assetsDir.absolutePath)
        intent.putExtra("minecraft_natives_dir", launchPaths.nativesDir.absolutePath)
'''
        if 'minecraft_client_jar' not in block:
            launch = block.find('startActivity(intent)')
            if launch >= 0:
                line_start = block.rfind('\n', 0, launch) + 1
                block = block[:line_start] + extras + block[line_start:]
            else:
                # A generated manager/activity can hand off through another call;
                # keep the gate but do not invent an Intent.
                pass
        s = s[:start] + block + s[end:]
    ui.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    source_root = root / "app/src/main/java"
    ui = find_one(source_root, "DroidLauncherUiActivity.kt")
    manager = find_one(source_root, "MinecraftLaunchManager.kt")
    patch_ui(ui)
    repair_manager_import_order(manager)

    text = ui.read_text(encoding="utf-8") + '\n' + manager.read_text(encoding="utf-8")
    for needle in (
        'MinecraftLaunchPaths.resolve(this, version)',
        'DROID_LAUNCH_PATHS_VERSION',
        'NativeGameBridge.launchJava(',
    ):
        if needle not in text:
            raise SystemExit(f"[step225] missing launch-path contract: {needle}")
    print('[step225] installed Minecraft filesystem paths resolved before launch')
    print('[step225] explicit client/library/assets/native paths added to launch intent when an Intent boundary exists')
    print('[step225] Kotlin imports remain before top-level declarations')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
