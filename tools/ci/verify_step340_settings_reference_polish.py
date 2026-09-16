#!/usr/bin/env python3
"""Verify Step 340 Settings reference visual polish contracts."""
from pathlib import Path
import sys

REQUIRED = [
    "// STEP340_SETTINGS_REFERENCE_POLISH",
    '"⚙  Settings"',
    'Color.rgb(231, 240, 249)',
    'if (page == "Renderer")',
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step340] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if missing:
        raise SystemExit("[step340] missing contracts: " + ", ".join(missing))
    print("[step340] Settings reference polish verification passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
