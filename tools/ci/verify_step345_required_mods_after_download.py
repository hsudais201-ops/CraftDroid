#!/usr/bin/env python3
from pathlib import Path
import sys

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step345-verify] generated UI missing")
    s = ui.read_text(encoding="utf-8")
    for item in ["STEP345_REQUIRED_MODS_AFTER_DOWNLOAD", "if (page == \"Modpack\") showRequiredModsForProject(slug, name)"]:
        if item not in s: raise SystemExit("[step345-verify] missing: " + item)
    print("[step345-verify] required-mod display after modpack download verified")
    return 0

if __name__ == "__main__": raise SystemExit(main())
