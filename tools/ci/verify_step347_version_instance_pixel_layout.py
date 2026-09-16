#!/usr/bin/env python3
"""Verify screenshot-matched Version / Instances UI contracts."""
from pathlib import Path
import sys

REQUIRED = [
    "// STEP347_VERSION_INSTANCE_PIXEL_LAYOUT",
    "title.visibility = android.view.View.GONE",
    'text = "⌂"',
    '"▰" to "Files"',
    '"♟" to "Accounts"',
    '"⇩" to "Downloads"',
    '"⚙" to "Settings"',
    'text = "+"',
    'contentDescription = "Add version"',
    'android.graphics.DashPathEffect',
    'isSingleLine = true',
    'contentDescription = "Delete row"',
    'contentDescription = "Open folder"',
    'dashedBorderPanel("back"',
    'dashedBorderPanel("Select"',
    'dashedBorderPanel("Create server"',
    'dashedBorderPanel("Coming soon"',
    'libraryPage("Game")',
    'setTextColor(android.graphics.Color.BLACK)',
]

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step347] missing UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if missing:
        raise SystemExit("[step347] missing contracts: " + ", ".join(missing))
    if s.count("// STEP347_VERSION_INSTANCE_PIXEL_LAYOUT") != 1:
        raise SystemExit("[step347] marker count is not exactly one")
    print("[step347] screenshot-matched toolbar, plus, dashed list, row actions and right rail verified")
    return 0

if __name__ == "__main__": raise SystemExit(main())
