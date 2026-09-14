#!/usr/bin/env python3
from pathlib import Path
import sys

APP_LABEL = "Droid Launcher"


def patch_manifest(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original = text
    if "android:label=\"@string/app_name\"" in text:
        text = text.replace('android:label="@string/app_name"', 'android:label="Droid Launcher"')
    if 'android:label="CraftDroid"' in text:
        text = text.replace('android:label="CraftDroid"', 'android:label="Droid Launcher"')
    if 'android:label="Zalith Launcher"' in text:
        text = text.replace('android:label="Zalith Launcher"', 'android:label="Droid Launcher"')
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return 'Droid Launcher' in text


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    manifests = list(root.glob("**/src/main/AndroidManifest.xml"))
    if not manifests:
        raise SystemExit(f"[branding] no AndroidManifest.xml under {root}")
    changed = sum(patch_manifest(p) for p in manifests)
    for p in root.glob("**/res/values/strings.xml"):
        text = p.read_text(encoding="utf-8")
        new = text.replace(">CraftDroid<", f">{APP_LABEL}<").replace(">Zalith Launcher<", f">{APP_LABEL}<")
        if new != text:
            p.write_text(new, encoding="utf-8")
    print(f"[branding] {APP_LABEL}; manifests={len(manifests)} changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
