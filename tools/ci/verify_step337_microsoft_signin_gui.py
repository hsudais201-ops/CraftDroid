#!/usr/bin/env python3
"""Step 337 verifier: fail closed on the Microsoft sign-in GUI and Home return action."""
from pathlib import Path
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step337-verify] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    text = find_ui(root).read_text(encoding="utf-8")
    required = (
        "private fun showMicrosoftSignInPage()",
        "private fun openMicrosoftLoginWebsite()",
        "android.content.Intent.ACTION_VIEW",
        "https://login.live.com/",
        "Sign in with Microsoft",
        'contentDescription = "Home - return to Droid Launcher"',
        'setOnClickListener { showPage("Game") }',
        "Skin\\nPreview",
        "Upload\\nskin",
        "Upload\\ncap",
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit("[step337-verify] missing contract(s): " + ", ".join(missing))
    entry = 'ms.setOnClickListener { showMicrosoftSignInPage() }'
    if entry not in text:
        raise SystemExit("[step337-verify] Accounts page does not open the custom Microsoft page")
    if 'ms.setOnClickListener { showMicrosoftAccountInfo() }' in text:
        raise SystemExit("[step337-verify] obsolete Microsoft placeholder remains")
    print("[step337-verify] Microsoft custom GUI + browser gate + top-right Home contracts verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
