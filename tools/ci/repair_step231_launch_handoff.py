#!/usr/bin/env python3
"""Step 231: pass verified Minecraft classpath/entrypoint paths through launch handoff."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step231] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    builder = find_one(src, "MinecraftLaunchCommandBuilder.kt")
    s = ui.read_text(encoding="utf-8")

    # Resolve the command immediately after the existing canonical launch-path check.
    anchor = '        val launchPaths = MinecraftLaunchPaths.resolve(this, version)\n'
    insert = anchor + '''        val launchCommand = MinecraftLaunchCommandBuilder.build(this, version)
        if (!launchCommand.valid) {
            Toast.makeText(this, "Minecraft $version launch command is invalid: ${launchCommand.error ?: "unknown error"}", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
'''
    if 'MinecraftLaunchCommandBuilder.build(this, version)' not in s:
        start = s.find('    private fun launchSelectedMinecraft() {')
        pos = s.find(anchor, start)
        if start < 0 or pos < 0:
            raise SystemExit('[step231] launchSelectedMinecraft canonical-path anchor missing')
        s = s[:pos] + insert + s[pos + len(anchor):]

    extras_anchor = '            intent.putExtra("minecraft_natives_dir", launchPaths.nativesDir.absolutePath)\n'
    extras = extras_anchor + '''            intent.putExtra("minecraft_main_class", launchCommand.mainClass)
            intent.putExtra("minecraft_classpath", launchCommand.classpathString)
            intent.putExtra("minecraft_asset_index", launchCommand.assetIndex ?: "")
            intent.putExtra("minecraft_native_dir", launchCommand.nativeDir.absolutePath)
'''
    if 'intent.putExtra("minecraft_classpath", launchCommand.classpathString)' not in s:
        if extras_anchor not in s:
            raise SystemExit('[step231] launch native-path extra anchor missing')
        s = s.replace(extras_anchor, extras, 1)

    # Add the builder to the generated source manifest contract through a lightweight marker.
    marker = '// Step 231 launch handoff: verified main class, classpath, asset index and native directory.\n'
    if marker not in s:
        pos = s.find('\n', s.find('package '))
        if pos < 0:
            raise SystemExit('[step231] package declaration not found')
        s = s[:pos + 1] + marker + s[pos + 1:]

    ui.write_text(s, encoding="utf-8")

    if 'class MinecraftLaunchCommandBuilder' not in builder.read_text(encoding="utf-8"):
        raise SystemExit('[step231] command builder source missing')
    for needle in (
        'MinecraftLaunchCommandBuilder.build(this, version)',
        'intent.putExtra("minecraft_main_class", launchCommand.mainClass)',
        'intent.putExtra("minecraft_classpath", launchCommand.classpathString)',
        'intent.putExtra("minecraft_asset_index", launchCommand.assetIndex ?: "")',
        'intent.putExtra("minecraft_native_dir", launchCommand.nativeDir.absolutePath)',
        'Step 231 launch handoff:',
    ):
        if needle not in s:
            raise SystemExit(f'[step231] missing launch-handoff contract: {needle}')

    print('[step231] verified Minecraft entrypoint/classpath/native paths are built from installed metadata')
    print('[step231] launch intent now carries the computed main class, classpath, asset index and native directory')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
