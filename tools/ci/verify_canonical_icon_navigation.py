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
        'nav.addView(step375Nav("←") { canonicalNavigateBack() })',
        '"⌂" to { canonicalNavigateHome() }',
        '"▰" to { canonicalOpenCurrentInstanceFolder() }',
        '"♟" to { showPage("Accounts") }',
        '"⇩" to { showPage("Content") }',
        '"⚙" to { showPage("Settings") }',
        "canonicalToggleSecureMode()",
        "canonicalExportInstanceConfig()",
        "canonicalServerPage()",
        "SIGN IN FROM MICROSOFT",
        '"OptiFine"',
        '"Legacy Fabric"',
        '"Forge"',
        '"NeoForge"',
        '"Modpack"',
        "MODRINTH",
        "CURSEFORGE",
        '"Any version"',
        'TOUCH CONTROLS',
        "Grass block version tile",
    )
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit("[canonical-nav-verify] missing: " + ", ".join(missing))
    for typo in ("Obtifine", "dofault", "mabile", "onnce", "acconding"):
        if typo in s:
            raise SystemExit(f"[canonical-nav-verify] typo remains: {typo}")
    if s.count("private fun canonicalServerPage()") != 1:
        raise SystemExit("[canonical-nav-verify] duplicate server page")
    if s.count('step375Button("TOUCH CONTROLS"') != 1:
        raise SystemExit("[canonical-nav-verify] duplicate Controls settings entry")
    print("[canonical-nav-verify] PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
