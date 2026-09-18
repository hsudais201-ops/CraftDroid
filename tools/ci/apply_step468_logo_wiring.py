#!/usr/bin/env python3
"""Install and wire the optimized Droid Launcher logo into the generated Android app."""
from pathlib import Path
import shutil
import sys

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    source = Path.cwd() / "app/src/main/res/drawable/droid_launcher_logo.webp"
    if not source.is_file():
        raise SystemExit(f"[step468] missing logo asset: {source}")

    res = root / "app/src/main/res/drawable"
    res.mkdir(parents=True, exist_ok=True)
    target = res / "droid_launcher_logo.webp"
    shutil.copy2(source, target)

    ui_candidates = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(ui_candidates) != 1:
        raise SystemExit(f"[step468] expected exactly one UI activity, found {len(ui_candidates)}")
    ui = ui_candidates[0]
    text = ui.read_text(encoding="utf-8")
    old = 'resources.getIdentifier("craftdroid_logo", "drawable", packageName)'
    new = 'resources.getIdentifier("droid_launcher_logo", "drawable", packageName)'
    if old in text:
        text = text.replace(old, new)
    elif 'resources.getIdentifier("droid_launcher_logo", "drawable", packageName)' not in text:
        raise SystemExit("[step468] logo ImageView resource lookup not found")
    ui.write_text(text, encoding="utf-8")

    import xml.etree.ElementTree as ET
    manifests = list((root / "app/src/main").rglob("AndroidManifest.xml"))
    if len(manifests) != 1:
        raise SystemExit(f"[step468] expected one manifest, found {len(manifests)}")
    manifest = manifests[0]
    tree = ET.parse(manifest)
    root_el = tree.getroot()
    android = "{http://schemas.android.com/apk/res/android}"
    root_el.set(android + "icon", "@drawable/droid_launcher_logo")
    root_el.set(android + "roundIcon", "@drawable/droid_launcher_logo")
    tree.write(manifest, encoding="utf-8", xml_declaration=True)
    print("[step468] optimized Droid Launcher logo installed and wired")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
