#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = "// STEP345_REQUIRED_MODS_AFTER_DOWNLOAD"

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step345] generated UI missing")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s: return 0
    target = '                    android.widget.Toast.makeText(this, "Download started: $filename", android.widget.Toast.LENGTH_LONG).show()'
    if target not in s: raise SystemExit("[step345] download success line not found")
    replacement = target + '\n                    // STEP345_REQUIRED_MODS_AFTER_DOWNLOAD\n                    if (page == "Modpack") showRequiredModsForProject(slug, name)'
    s = s.replace(target, replacement, 1)
    ui.write_text(s, encoding="utf-8")
    print("[step345] required-mod dialog is now shown after a modpack download")
    return 0

if __name__ == "__main__": raise SystemExit(main())
