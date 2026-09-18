#!/usr/bin/env python3
"""Verify the optimized Droid Launcher logo wiring."""
from pathlib import Path
import sys

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    asset = root / "app/src/main/res/drawable/droid_launcher_logo.webp"
    if not asset.is_file() or asset.stat().st_size <= 0:
        raise SystemExit("[step468] logo asset missing or empty")
    ui = next((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"), None)
    if ui is None:
        raise SystemExit("[step468] UI activity missing")
    text = ui.read_text(encoding="utf-8")
    if 'resources.getIdentifier("droid_launcher_logo", "drawable", packageName)' not in text:
        raise SystemExit("[step468] UI is not using droid_launcher_logo")
    if 'craftdroid_logo", "drawable"' in text:
        raise SystemExit("[step468] old UI logo lookup remains")
    manifests = list((root / "app/src/main").rglob("AndroidManifest.xml"))
    if len(manifests) != 1:
        raise SystemExit(f"[step468] expected one manifest, found {len(manifests)}")
    manifest_text = manifests[0].read_text(encoding="utf-8")
    if '@drawable/droid_launcher_logo' not in manifest_text:
        raise SystemExit("[step468] manifest icon wiring missing")
    print("[step468] optimized logo asset, UI lookup and manifest icon wiring: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
