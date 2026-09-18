#!/usr/bin/env python3
"""Step 461 verification."""
from pathlib import Path
import sys

UI = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
MANIFEST = Path("app/src/main/AndroidManifest.xml")
LOGO = Path("app/src/main/res/drawable/craftdroid_logo.xml")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / UI
    manifest = root / MANIFEST
    logo = root / LOGO
    for path in (ui, manifest, logo):
        if not path.is_file():
            raise SystemExit("[step461-verify] missing " + str(path))

    s = ui.read_text(encoding="utf-8")
    m = manifest.read_text(encoding="utf-8")
    x = logo.read_text(encoding="utf-8")

    required = (
        "// STEP461_REAL_LOGO_AND_MEMORY",
        'resources.getIdentifier("craftdroid_logo", "drawable", packageName)',
        'android:icon="@drawable/craftdroid_logo"',
        'android:roundIcon="@drawable/craftdroid_logo"',
        "<vector",
        "android:viewportWidth=\"108\"",
        "android:viewportHeight=\"108\"",
        "step376LowRam",
    )
    joined = s + "\n" + m + "\n" + x
    missing = [v for v in required if v not in joined]
    if missing:
        raise SystemExit("[step461-verify] missing: " + ", ".join(missing))

    if s.count("// STEP461_REAL_LOGO_AND_MEMORY") != 1:
        raise SystemExit("[step461-verify] duplicate Step461 marker")

    print("[step461-verify] real vector branding and low-RAM UI integration pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
