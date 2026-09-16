#!/usr/bin/env python3
"""Verify Step 343 content download and Worlds contracts."""
from pathlib import Path
import sys

REQUIRED = [
    "STEP343_ONE_CLICK_DOWNLOAD_REQUIRED_WORLD",
    "downloadContent(page, name)",
    "contentSlug(page: String, name: String)",
    "DownloadManager.Request",
    "api.modrinth.com/v2/project/",
    "showRequiredModsForProject",
    "dependencies",
    "World",
    "worldsPage()",
    "Import world",
    "Create New World",
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step343-verify] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in s]
    if missing:
        raise SystemExit("[step343-verify] missing contracts: " + ", ".join(missing))
    if "startContentImport(page)" in s:
        raise SystemExit("[step343-verify] old picker-only action remains in download rows")
    print("[step343-verify] one-click download, required dependency, and World contracts verified")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
