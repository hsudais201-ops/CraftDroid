#!/usr/bin/env python3
from pathlib import Path
import sys

REQUIRED = [
    "STEP344_DOWNLOAD_WORLD_AND_DEPENDENCIES",
    "downloadContent(page, name)",
    "DownloadManager.Request",
    "api.modrinth.com/v2/project/",
    "showRequiredModsForProject",
    "dependencies",
    "worldsPage()",
    "Import world",
    "Download World",
    "Open World Folder",
]

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step344-verify] generated UI missing")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if missing: raise SystemExit("[step344-verify] missing: " + ", ".join(missing))
    if "startContentImport(page)" in s: raise SystemExit("[step344-verify] picker-only content action remains")
    print("[step344-verify] one-click downloads, required mods, and Worlds contracts verified")
    return 0

if __name__ == "__main__": raise SystemExit(main())
