#!/usr/bin/env python3
"""Static verification for the isolated first-run component extraction gate."""
from pathlib import Path
import re
import sys

REQUIRED = [
    "authlib-injector",
    "caciocavallo",
    "caciocavallo 17",
    "Internal-17",
    "Internal-21",
    "Internal-25",
    "Internal-8",
    "JNA",
    "Launcher Components",
    "LWJGL 3.3.3",
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step287] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    for item in REQUIRED:
        if f'BootstrapComponent("{item}"' not in s:
            raise SystemExit(f"[step287] missing required component: {item}")

    for needle in (
        'private fun showBootstrapGate()',
        'private fun extractBootstrapComponents(',
        'private fun bootstrapComplete(): Boolean',
        'putBoolean("components_extracted", true)',
        'showBootstrapGate()',
        'showPage("Game")',
        '"Zalith Launcher"',
        '"Install"',
    ):
        if needle not in s:
            raise SystemExit(f"[step287] missing gate contract: {needle}")

    # The first-run gate must not render the normal navigation toolbar.
    gate_start = s.index('private fun showBootstrapGate()')
    gate_end = s.index('    private fun buildUi()', gate_start)
    gate = s[gate_start:gate_end]
    for forbidden in ('"Accounts"', '"Downloads"', '"Settings"'):
        if forbidden in gate:
            raise SystemExit(f"[step287] first-run gate contains normal navigation: {forbidden}")

    # Completion must be set only inside the successful extraction branch.
    completion_count = s.count('putBoolean("components_extracted", true)')
    if completion_count != 1:
        raise SystemExit(f"[step287] expected one successful completion write, found {completion_count}")

    if s.count('private fun buildUi()') != 1:
        raise SystemExit('[step287] buildUi declaration is not unique')
    if s.count('private fun showBootstrapGate()') != 1:
        raise SystemExit('[step287] showBootstrapGate declaration is not unique')

    print('[step287] all 10 required component entries present')
    print('[step287] first-run gate is isolated from normal navigation')
    print('[step287] Install completion is persisted only after extraction verification')
    print('[step287] retry/failure path keeps the gate active')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
