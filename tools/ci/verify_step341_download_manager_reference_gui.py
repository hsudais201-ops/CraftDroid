#!/usr/bin/env python3
"""Verify the Step 341 3.jpeg-based download/install UI contracts."""
from pathlib import Path
import sys

MARKER = "// STEP341_DOWNLOAD_MANAGER_REFERENCE_GUI"
REQUIRED = [
    'title.text = "Download - $titleName"',
    '✓  Release',
    'Snapshot',
    'April Fools',
    'Old Versions',
    'hint = "Search"',
    'Select Minecraft version',
    'showVersionSelectionDialog',
    'Select loader',
    'showLoaderSelectionDialog',
    'Fabric',
    'Forge',
    'NeoForge',
    'Quilt',
    'OptiFine',
    'selectedMinecraftVersion',
    'selectedLoader',
    'optiFineEnabled',
    '"Modpack" ->',
    '"Mod" ->',
    '"Resource Pack" ->',
    '"Shader Pack" ->',
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step341] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if MARKER not in s:
        missing.append(MARKER)
    if missing:
        raise SystemExit("[step341] missing contracts: " + ", ".join(missing))
    print("[step341] 3.jpeg download/install/version GUI verification passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

# Post-fix trigger: force a clean CI run from the current generator chain.
