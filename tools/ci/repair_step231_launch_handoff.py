#!/usr/bin/env python3
"""Step 231/238: pass verified Minecraft launch inputs through the UI handoff.

The generated Step 153 launcher can expose the native-directory path under either
Step 225's plural extra or a direct launch-native extra. Keep the repair
pattern-based and fail closed only when no Intent boundary exists at all.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step231] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def nearest_method(s: str, pos: int) -> tuple[int, str]:
    start = s.rfind("    private fun ", 0, pos)
    if start < 0:
        raise SystemExit("[step231] launch method declaration not found before launch-path marker")
    line_end = s.find("\n", start)
    if line_end < 0:
        line_end = len(s)
    return start, s[start:line_end]


def insert_after_line(s: str, anchor_regex: str, insertion: str) -> bool:
    match = re.search(anchor_regex, s)
    if not match:
        return False
    line_end = s.find("\n", match.end())
    if line_end < 0:
        line_end = len(s)
    s_new = s[:line_end + 1] + insertion + s[line_end + 1:]
    return s_new


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    builder = find_one(src, "MinecraftLaunchCommandBuilder.kt")
    s = ui.read_text(encoding="utf-8")

    anchor = '        val launchPaths = MinecraftLaunchPaths.resolve(this, version)\n'
    pos = s.find(anchor)
    if pos < 0:
        raise SystemExit('[step231] canonical launch-path marker missing')
    method_start, method_decl = nearest_method(s, pos)

    launch_builder = '        val launchCommand = MinecraftLaunchCommandBuilder.build(this, version)\n'
    insertion = launch_builder + '''        if (!launchCommand.valid) {\n            Toast.makeText(this, "Minecraft $version launch command is invalid: ${launchCommand.error ?: "unknown error"}", Toast.LENGTH_LONG).show()\n            showPage("Search by ID")\n            return\n        }\n'''
    if launch_builder not in s:
        s = s[:pos] + anchor + insertion + s[pos + len(anchor):]

    # Prefer the Step 225 plural native-dir extra when present.
    extras = '''            intent.putExtra("minecraft_main_class", launchCommand.mainClass)\n            intent.putExtra("minecraft_classpath", launchCommand.classpathString)\n            intent.putExtra("minecraft_asset_index", launchCommand.assetIndex ?: "")\n            intent.putExtra("minecraft_native_dir", launchCommand.nativeDir.absolutePath)\n'''
    if 'intent.putExtra("minecraft_classpath", launchCommand.classpathString)' not in s:
        native_anchor_patterns = (
            r'^\s*intent\.putExtra\("minecraft_natives_dir", launchPaths\.nativesDir\.absolutePath\)\s*$',
            r'^\s*intent\.putExtra\("minecraft_native_dir", launchPaths\.nativesDir\.absolutePath\)\s*$',
        )
        updated = None
        for pattern in native_anchor_patterns:
            candidate = insert_after_line(s, pattern, extras)
            if candidate:
                updated = candidate
                break
        if updated is None:
            # Some generated variants already have an Intent but no Step-225 native extra.
            # Anchor after the first launch-related extra in the selected method.
            method_end = s.find("\n    private fun ", method_start + 1)
            if method_end < 0:
                method_end = len(s)
            method = s[method_start:method_end]
            generic = re.search(r'^\s*intent\.putExtra\([^\n]+\)\s*$', method, re.MULTILINE)
            if generic:
                abs_line_end = method_start + generic.end()
                newline = s.find("\n", abs_line_end)
                if newline < 0:
                    newline = abs_line_end
                updated = s[:newline + 1] + extras + s[newline + 1:]
        if updated is None:
            raise SystemExit('[step231] no usable launch Intent extra anchor found')
        s = updated

    marker = '// Step 231 launch handoff: verified main class, classpath, asset index and native directory.\n'
    if marker not in s:
        package_end = s.find('\n', s.find('package '))
        if package_end < 0:
            raise SystemExit('[step231] package declaration not found')
        s = s[:package_end + 1] + marker + s[package_end + 1:]

    ui.write_text(s, encoding="utf-8")
    builder_text = builder.read_text(encoding="utf-8")
    if 'object MinecraftLaunchCommandBuilder' not in builder_text:
        raise SystemExit('[step231] MinecraftLaunchCommandBuilder.kt is invalid')
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

    print(f'[step231] launch handoff inserted into {method_decl.strip()}')
    print('[step231] launch command is built from the selected installed version metadata')
    print('[step231] computed main class, classpath, asset index and native directory are passed to launch')
    print('[step238] native-directory extra anchor now accepts generated launcher variants')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
