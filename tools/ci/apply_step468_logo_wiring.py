#!/usr/bin/env python3
"""Install and wire the optimized Droid Launcher logo without rewriting XML namespaces."""
from pathlib import Path
import re
import shutil
import sys

ANDROID_NS = "http://schemas.android.com/apk/res/android"

def set_manifest_logo(text: str) -> str:
    match = re.search(r"<manifest\b[^>]*>", text, flags=re.DOTALL)
    if not match:
        raise SystemExit("[step468] manifest root tag not found")
    opening = match.group(0)
    if "xmlns:android=" not in opening:
        opening = opening[:-1] + f' xmlns:android="{ANDROID_NS}">'
    opening = re.sub(r'\s+android:(?:icon|roundIcon)="[^"]*"', "", opening)
    if opening.endswith("/>"):
        opening = opening[:-2] + ' android:icon="@drawable/droid_launcher_logo" android:roundIcon="@drawable/droid_launcher_logo"/>'
    else:
        opening = opening[:-1] + ' android:icon="@drawable/droid_launcher_logo" android:roundIcon="@drawable/droid_launcher_logo">'
    return text[:match.start()] + opening + text[match.end():]

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    source = Path.cwd() / "app/src/main/res/drawable/droid_launcher_logo.webp"
    if not source.is_file():
        raise SystemExit(f"[step468] missing logo asset: {source}")

    res = root / "app/src/main/res/drawable"
    res.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, res / "droid_launcher_logo.webp")

    ui_candidates = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(ui_candidates) != 1:
        raise SystemExit(f"[step468] expected exactly one UI activity, found {len(ui_candidates)}")
    ui = ui_candidates[0]
    text = ui.read_text(encoding="utf-8")
    old = 'resources.getIdentifier("craftdroid_logo", "drawable", packageName)'
    new = 'resources.getIdentifier("droid_launcher_logo", "drawable", packageName)'
    if old in text:
        text = text.replace(old, new)
    elif new not in text:
        raise SystemExit("[step468] logo ImageView resource lookup not found")
    ui.write_text(text, encoding="utf-8")

    manifests = list((root / "app/src/main").rglob("AndroidManifest.xml"))
    if len(manifests) != 1:
        raise SystemExit(f"[step468] expected one manifest, found {len(manifests)}")
    manifest = manifests[0]
    manifest.write_text(set_manifest_logo(manifest.read_text(encoding="utf-8")), encoding="utf-8")
    print("[step468] optimized Droid Launcher logo installed and wired with namespace preserved")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
