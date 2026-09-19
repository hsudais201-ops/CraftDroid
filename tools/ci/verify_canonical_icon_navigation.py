#!/usr/bin/env python3
from pathlib import Path
import sys

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = next((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"), None)
    if ui is None:
        raise SystemExit("[canonical-nav-verify] UI missing")
    s = ui.read_text(encoding="utf-8", errors="replace")
    required = (
        "CANONICAL_ICON_NAVIGATION",
        "canonicalNavigateBack",
        "canonicalNavigateHome",
        "canonicalOpenCurrentInstanceFolder",
        "canonicalExportInstanceConfig",
        "canonicalBrowsePage",
        "canonicalVersionPage",
        "canonicalToggleSecureMode",
        "SIGN IN FROM MICROSOFT",
        '"OptiFine"',
        '"Legacy Fabric"',
        '"Forge"',
        '"NeoForge"',
        '"Modpack"',
        "MODRINTH",
        "Any version",
        "TOUCH CONTROLS",
        "Grass block version tile",
        "Tap to edit server name or address",
        "Live ping / connection quality",
    )
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit("[canonical-nav-verify] missing: " + ", ".join(missing))
    if ('nav.addView(step375Nav("←") { canonicalNavigateBack() })' not in s and
        '"←  Back" to { canonicalNavigateBack() }' not in s and
        'val back = button("←")' not in s):
        raise SystemExit("[canonical-nav-verify] back navigation is not wired")
    if ('"⌂" to { canonicalNavigateHome() }' not in s and
        '"⌂  Home" to { canonicalNavigateHome() }' not in s and
        'val home = button("⌂")' not in s):
        raise SystemExit("[canonical-nav-verify] home navigation is not wired")
    if ('"▰" to { canonicalOpenCurrentInstanceFolder() }' not in s and
        '"▰  Files" to { canonicalOpenCurrentInstanceFolder() }' not in s and
        'val files = button("▰")' not in s):
        raise SystemExit("[canonical-nav-verify] folder navigation is not wired")
    for typo in ("Obtifine", "dofault", "mabile", "onnce", "acconding"):
        if typo in s:
            raise SystemExit(f"[canonical-nav-verify] typo remains: {typo}")
    if s.count("private fun canonicalBrowsePage()") != 1:
        raise SystemExit("[canonical-nav-verify] duplicate browse page helper")
    if s.count("private fun canonicalVersionPage()") != 1:
        raise SystemExit("[canonical-nav-verify] duplicate version page helper")
    if s.count('step375Button("TOUCH CONTROLS"') != 1:
        raise SystemExit("[canonical-nav-verify] duplicate Controls settings entry")
    if ("step479Servers()" in s or "STEP481_RUNTIME_FINISHING" in s) and "step481ServerIcon" not in s:
        raise SystemExit("[canonical-nav-verify] real server favicon renderer is not preserved")
    print("[canonical-nav-verify] PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
