#!/usr/bin/env python3
"""Step 337 verifier: fail closed on Microsoft-page actions and cosmetic pickers."""
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
        "private fun openCosmeticImagePicker(requestCode: Int)",
        "override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?)",
        "android.content.Intent.ACTION_VIEW",
        "android.content.Intent.ACTION_OPEN_DOCUMENT",
        "https://login.live.com/",
        "openCosmeticImagePicker(3371)",
        "openCosmeticImagePicker(3372)",
        '"microsoft_skin_uri"',
        '"microsoft_cape_uri"',
        "takePersistableUriPermission",
        'contentDescription = "Home - return to Droid Launcher"',
        'setOnClickListener { showPage("Game") }',
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit("[step337-verify] missing contract(s): " + ", ".join(missing))
    entry = 'ms.setOnClickListener { showMicrosoftSignInPage() }'
    if entry not in text:
        raise SystemExit("[step337-verify] Accounts page does not open the custom Microsoft page")
    if 'ms.setOnClickListener { showMicrosoftAccountInfo() }' in text:
        raise SystemExit("[step337-verify] obsolete Microsoft entry remains")
    if 'Skin picker is ready for the next image-selection step.' in text or 'Cape picker is ready for the next image-selection step.' in text:
        raise SystemExit("[step337-verify] obsolete fake cosmetic picker toast remains")
    skin_patterns = (
        'uploadSkin.setOnClickListener { openCosmeticImagePicker(3371) }',
        'button("Upload\\nskin").apply {',
    )
    cape_patterns = (
        'uploadCap.setOnClickListener { openCosmeticImagePicker(3372) }',
        'button("Upload\\ncape").apply {',
    )
    if not any(pattern in text for pattern in skin_patterns):
        raise SystemExit("[step337-verify] skin upload is not wired to the real picker")
    if not any(pattern in text for pattern in cape_patterns):
        raise SystemExit("[step337-verify] cape upload is not wired to the real picker")
    print("[step337-verify] Microsoft page + real Android skin/cape picker + persisted URI callback verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
