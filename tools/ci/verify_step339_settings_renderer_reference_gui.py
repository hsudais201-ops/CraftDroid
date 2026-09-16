#!/usr/bin/env python3
"""Verify the Step 339 Settings · Renderer reference GUI contract."""
from pathlib import Path
import sys

MARKER = "// STEP339_SETTINGS_RENDERER_REFERENCE_GUI"
REQUIRED = (
    'title.text = "Settings · Renderer"',
    'addReferenceSetting(rendererCard, "Global Renderer"',
    'addReferenceSetting(rendererCard, "Vulkan Driver"',
    'addReferenceSetting(rendererCard, "Graphics API"',
    'addReferenceSetting(resolutionRule, "Resolution Rule"',
    'label("Resolution Scale"',
    'label("Game Fullscreen"',
    'showRendererChoiceDialog("Global Renderer"',
    'showRendererChoiceDialog("Vulkan Driver"',
    'showRendererChoiceDialog("Graphics API"',
)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step339-verify] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [token for token in (MARKER,) + REQUIRED if token not in s]
    if missing:
        raise SystemExit("[step339-verify] missing contracts: " + ", ".join(missing))
    if 'setSingleChoiceItems' not in s:
        raise SystemExit("[step339-verify] renderer selection dialog behavior missing")
    if 'android.widget.SeekBar.OnSeekBarChangeListener' not in s:
        raise SystemExit("[step339-verify] resolution scale interaction missing")
    if 'contentDescription = "Game Fullscreen"' not in s:
        raise SystemExit("[step339-verify] fullscreen toggle contract missing")
    print("[step339-verify] Settings · Renderer reference GUI contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
