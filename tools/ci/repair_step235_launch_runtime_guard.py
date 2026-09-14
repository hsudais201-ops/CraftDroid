#!/usr/bin/env python3
"""Step 235: enforce that the Android activity validates the handoff before launch.

The generated MinecraftLaunchManager executes below the activity boundary and does
not own an Android Intent. Step 234 is therefore the authoritative runtime gate;
this step verifies that contract rather than manufacturing a fake Intent.
"""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step235] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    ui_path = find_one(src, "DroidLauncherUiActivity.kt")
    manager_path = find_one(src, "MinecraftLaunchManager.kt")
    handoff = find_one(src, "MinecraftLaunchHandoff.kt")
    validator = find_one(src, "MinecraftLaunchHandoffValidator.kt")

    ui = ui_path.read_text(encoding="utf-8")
    manager = manager_path.read_text(encoding="utf-8")

    required_ui = (
        'MinecraftLaunchHandoffReader.read(intent)',
        'MinecraftLaunchHandoffValidator.validate(this, launchHandoff)',
        'if (handoffError != null)',
        'Toast.makeText(this, "Launch blocked: $handoffError", Toast.LENGTH_LONG).show()',
        'startActivity(intent)',
    )
    for needle in required_ui:
        if needle not in ui:
            raise SystemExit(f"[step235] activity handoff gate missing: {needle}")

    read_pos = ui.find('MinecraftLaunchHandoffReader.read(intent)')
    launch_pos = ui.find('startActivity(intent)', read_pos)
    if read_pos < 0 or launch_pos < 0 or read_pos > launch_pos:
        raise SystemExit('[step235] activity handoff validation is not before startActivity(intent)')

    if 'NativeGameBridge.launchJava(' not in manager:
        raise SystemExit('[step235] generated Minecraft runtime launch call is missing')
    if 'object MinecraftLaunchHandoffReader' not in handoff.read_text(encoding='utf-8'):
        raise SystemExit('[step235] launch handoff reader missing')
    if 'object MinecraftLaunchHandoffValidator' not in validator.read_text(encoding='utf-8'):
        raise SystemExit('[step235] launch handoff validator missing')

    print('[step235] Android activity validates the concrete Minecraft handoff before startActivity(intent)')
    print('[step235] generated runtime retains its real NativeGameBridge.launchJava call without a fabricated Intent')
    print('[step235] launch boundary is fail-closed on invalid handoff data')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
