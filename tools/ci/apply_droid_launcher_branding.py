#!/usr/bin/env python3
"""Step 194: apply the Droid Launcher product name and app icon to the extracted Android project."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ANDROID_NS = "http://schemas.android.com/apk/res/android"
ET.register_namespace("android", ANDROID_NS)

ICON_XML = '''<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#111827" android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#38bdf8" android:pathData="M22,18h42c18,0 30,12 30,36s-12,36 -30,36H22z"/>
    <path android:fillColor="#111827" android:pathData="M40,34h22c10,0 16,7 16,20s-6,20 -16,20H40z"/>
    <path android:fillColor="#f8fafc" android:pathData="M40,34h12v40H40z"/>
    <path android:fillColor="#f8fafc" android:pathData="M58,34h4c10,0 16,7 16,20s-6,20 -16,20h-4V62h4c3,0 5,-3 5,-8s-2,-8 -5,-8h-4z"/>
    <path android:fillColor="#a5f3fc" android:pathData="M22,18h12v12H22zM22,78h12v12H22z"/>
</vector>
'''


def find_single(root: Path, pattern: str, label: str) -> Path:
    matches = list(root.rglob(pattern))
    if not matches:
        raise SystemExit(f"{label}: no match for {pattern}")
    if len(matches) > 1:
        matches.sort(key=lambda p: (len(p.parts), str(p)))
    return matches[0]


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    manifest = find_single(root, "AndroidManifest.xml", "Android manifest")
    tree = ET.parse(manifest)
    app_nodes = tree.getroot().findall("application")
    if not app_nodes:
        raise SystemExit(f"Droid branding: application node not found in {manifest}")
    app = app_nodes[0]
    app.set(f"{{{ANDROID_NS}}}label", "Droid Launcher")
    app.set(f"{{{ANDROID_NS}}}icon", "@drawable/ic_droid_launcher")
    app.set(f"{{{ANDROID_NS}}}roundIcon", "@drawable/ic_droid_launcher")
    tree.write(manifest, encoding="utf-8", xml_declaration=True)
    print(f"[branding] Android label/icon updated in {manifest}")

    res_dirs = list(root.rglob("res"))
    if not res_dirs:
        raise SystemExit("Droid branding: Android res directory not found")
    res = sorted(res_dirs, key=lambda p: (len(p.parts), str(p)))[0]
    drawable = res / "drawable"
    drawable.mkdir(parents=True, exist_ok=True)
    icon = drawable / "ic_droid_launcher.xml"
    icon.write_text(ICON_XML, encoding="utf-8")
    print(f"[branding] Droid Launcher icon written to {icon}")

    # Update common launcher-facing string resources without touching package/class names.
    string_files = list(res.rglob("strings.xml"))
    changed = 0
    for path in string_files:
        text = path.read_text(encoding="utf-8")
        new = re.sub(r'(<string\s+name=["\'](?:app_name|launcher_name)["\'][^>]*>).*?(</string>)', r'\1Droid Launcher\2', text, flags=re.IGNORECASE | re.DOTALL)
        if new != text:
            path.write_text(new, encoding="utf-8")
            changed += 1
            print(f"[branding] Updated launcher name in {path}")
    if changed == 0:
        print("[branding] No app_name/launcher_name string resource found; manifest label remains authoritative.")

    print("[branding] Step 194 Droid Launcher branding complete")


if __name__ == "__main__":
    main()
