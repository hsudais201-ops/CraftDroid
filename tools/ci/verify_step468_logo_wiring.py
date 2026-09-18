#!/usr/bin/env python3
"""Verify the optimized Droid Launcher logo wiring and Android manifest namespace."""
from pathlib import Path
import re
import sys

ANDROID_NS = "http://schemas.android.com/apk/res/android"

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    asset = root / "app/src/main/res/drawable/droid_launcher_logo.webp"
    if not asset.is_file() or asset.stat().st_size <= 0:
        raise SystemExit("[step468] logo asset missing or empty")
    ui_candidates = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(ui_candidates) != 1:
        raise SystemExit(f"[step468] expected one UI activity, found {len(ui_candidates)}")
    text = ui_candidates[0].read_text(encoding="utf-8")
    if 'resources.getIdentifier("droid_launcher_logo", "drawable", packageName)' not in text:
        raise SystemExit("[step468] UI is not using droid_launcher_logo")
    manifests = list((root / "app/src/main").rglob("AndroidManifest.xml"))
    if len(manifests) != 1:
        raise SystemExit(f"[step468] expected one manifest, found {len(manifests)}")
    manifest_text = manifests[0].read_text(encoding="utf-8")
    opening = re.search(r"<manifest\b[^>]*>", manifest_text, flags=re.DOTALL)
    if not opening:
        raise SystemExit("[step468] manifest root tag missing")
    root_tag = opening.group(0)
    if f'xmlns:android="{ANDROID_NS}"' not in root_tag:
        raise SystemExit("[step468] android namespace declaration missing")
    if root_tag.count('android:icon=') != 1 or '@drawable/droid_launcher_logo' not in root_tag:
        raise SystemExit("[step468] manifest icon wiring invalid")
    if root_tag.count('android:roundIcon=') != 1 or '@drawable/droid_launcher_logo' not in root_tag:
        raise SystemExit("[step468] manifest roundIcon wiring invalid")
    if re.search(r'(<uses-permission|<activity|<application)[^>]*\bandroid:', manifest_text) and f'xmlns:android="{ANDROID_NS}"' not in root_tag:
        raise SystemExit("[step468] android-prefixed manifest attributes are unbound")
    print("[step468] optimized logo, UI lookup, manifest namespace, icon and roundIcon: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
