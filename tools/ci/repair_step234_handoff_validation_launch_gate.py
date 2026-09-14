#!/usr/bin/env python3
"""Step 234: enforce launch-handoff validation before starting Minecraft runtime.

The consolidated source is generated from the Step 153 archive, so this repair
patches the generated launcher UI rather than modifying a missing checked-in
MinecraftLaunchManager implementation directly.
"""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step234] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    validator = find_one(root / "app/src/main/java", "MinecraftLaunchHandoffValidator.kt")
    handoff = find_one(root / "app/src/main/java", "MinecraftLaunchHandoff.kt")
    text = ui.read_text(encoding="utf-8")

    anchor = '        startActivity(intent)\n'
    gate = '''        val launchHandoff = MinecraftLaunchHandoffReader.read(intent)\n        val handoffError = MinecraftLaunchHandoffValidator.validate(this, launchHandoff)\n        if (handoffError != null) {\n            Toast.makeText(this, "Launch blocked: $handoffError", Toast.LENGTH_LONG).show()\n            return\n        }\n'''

    if 'MinecraftLaunchHandoffValidator.validate(this, launchHandoff)' not in text:
        # Only patch the first activity launch after the Step 231 command builder extras.
        marker = 'intent.putExtra("minecraft_root", launchPaths.minecraftRoot.absolutePath)'
        pos = text.find(marker)
        if pos < 0:
            raise SystemExit('[step234] Minecraft launch-root extra marker not found')
        launch_pos = text.find(anchor, pos)
        if launch_pos < 0:
            raise SystemExit('[step234] launch startActivity(intent) anchor not found after Minecraft handoff producer')
        text = text[:launch_pos] + gate + text[launch_pos:]
        ui.write_text(text, encoding='utf-8')

    ui_text = ui.read_text(encoding='utf-8')
    for needle in (
        'MinecraftLaunchHandoffReader.read(intent)',
        'MinecraftLaunchHandoffValidator.validate(this, launchHandoff)',
        'if (handoffError != null)',
        'Toast.makeText(this, "Launch blocked: $handoffError", Toast.LENGTH_LONG).show()',
        anchor,
    ):
        if needle not in ui_text:
            raise SystemExit(f'[step234] missing launch gate contract: {needle}')

    if 'object MinecraftLaunchHandoffValidator' not in validator.read_text(encoding='utf-8'):
        raise SystemExit('[step234] handoff validator implementation missing')
    if 'object MinecraftLaunchHandoffReader' not in handoff.read_text(encoding='utf-8'):
        raise SystemExit('[step234] handoff reader implementation missing')

    print('[step234] concrete Minecraft handoff is read and validated before runtime activity launch')
    print('[step234] invalid paths/root/version/classpath/native directory block launch with user feedback')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
