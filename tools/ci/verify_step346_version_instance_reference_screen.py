#!/usr/bin/env python3
"""Verify Step346 Version / Instances screen contracts."""
from pathlib import Path
import sys

MARKER = "// STEP346_VERSION_INSTANCE_REFERENCE_SCREEN"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step346] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    checks = {
        "marker": MARKER,
        "page": 'private fun showVersionInstancesPage()',
        "home_version": 'versionButton.setOnClickListener { showVersionInstancesPage() }',
        "home_instance": 'instanceButton.setOnClickListener { showVersionInstancesPage() }',
        "plus_description": 'add.contentDescription = "Add version or instance"',
        "plus_click": 'add.setOnClickListener {',
        "plus_download": 'libraryPage("Game")',
        "version_section": 'Installed Versions',
        "instance_section": 'Instances',
        "selected_version": 'Version  ·  ${selectedMinecraftVersion()}',
        "selected_instance": 'Instance  ·  ${selectedMinecraftProfile()}',
    }
    missing = [name for name, token in checks.items() if token not in s]
    if missing:
        raise SystemExit(f"[step346] missing contracts: {', '.join(missing)}")
    if s.count('private fun showVersionInstancesPage()') != 1:
        raise SystemExit("[step346] screen method count is not exactly one")
    print("[step346] Version / Instances screen verified")
    print("[step346] Version and Instance Home clicks verified")
    print("[step346] + -> Step341 Game download/version manager verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
