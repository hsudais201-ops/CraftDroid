#!/usr/bin/env python3
"""Step 338 verifier: fail closed on the reference-style Offline profile GUI."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step338-verify] generated launcher UI is missing")
    text = ui.read_text(encoding="utf-8")
    required = (
        "// STEP338_OFFLINE_PROFILE_REFERENCE_GUI",
        "private fun showOfflineProfileReferenceGui()",
        "private fun showOfflineAccountDialog()",
        "Add Offline Account",
        "showOfflineProfileReferenceGui()",
        "Skin\\nPreview",
        "cap\\nPreview",
        "Upload\\nskin",
        "Upload\\ncap",
        "Cosmetic",
        'contentDescription = "Home"',
        'setOnClickListener { showPage("Game") }',
        'button("+")',
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit("[step338-verify] missing contract(s): " + ", ".join(missing))
    if text.count("private fun showOfflineProfileReferenceGui()") != 1:
        raise SystemExit("[step338-verify] offline profile GUI helper must have exactly one declaration")
    if text.count("// STEP338_OFFLINE_PROFILE_REFERENCE_GUI") != 1:
        raise SystemExit("[step338-verify] offline profile GUI marker count is not one")
    expected = '''                addAccount("Offline", input.text.toString())\n                showOfflineProfileReferenceGui()'''
    if expected not in text:
        raise SystemExit("[step338-verify] Offline Add action does not open the reference GUI")
    print("[step338-verify] Offline account add -> reference GUI contract verified")
    print("[step338-verify] skin/cap/upload/cosmetic layout contract verified")
    print("[step338-verify] Home return action verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
