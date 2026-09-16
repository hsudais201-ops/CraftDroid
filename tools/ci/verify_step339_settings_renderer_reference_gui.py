#!/usr/bin/env python3
"""Verify the Step 339 Settings · Renderer reference GUI contracts."""
from pathlib import Path
import sys

MARKER = "// STEP339_SETTINGS_RENDERER_REFERENCE_GUI"
REQUIRED = [
    'title.text = "Settings · Renderer"',
    'Global Renderer',
    'Krypton Wrapper',
    'Vulkan Driver',
    'Turnip',
    'Graphics API',
    'Resolution Rule',
    'Resolution Scale',
    'Game Fullscreen',
    'showRendererChoiceDialog',
    'android.widget.SeekBar.OnSeekBarChangeListener',
    'android.widget.Switch(this)',
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step339] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if MARKER not in s:
        missing.append(MARKER)
    if missing:
        raise SystemExit("[step339] missing contracts: " + ", ".join(missing))
    if 'private fun rendererPage()' not in s or 'private fun javaPage()' not in s:
        raise SystemExit("[step339] renderer/java page boundaries missing")
    print("[step339] Settings · Renderer reference GUI verification passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
