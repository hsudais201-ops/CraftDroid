#!/usr/bin/env python3
"""Verify real content import wiring for the Step 342 install buttons."""
from pathlib import Path
import sys

MARKER = "// STEP342_CONTENT_INSTALL_PICKER"
REQUIRED = [
    'override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?)',
    'Intent.ACTION_OPEN_DOCUMENT',
    'CONTENT_PICKER_REQUEST',
    'private var pendingContentPage: String?',
    'MinecraftContentManager.Kind.MODPACK',
    'MinecraftContentManager.Kind.MOD',
    'MinecraftContentManager.Kind.SHADER',
    'MinecraftContentManager.Kind.RESOURCE_PACK',
    'MinecraftContentManager.importArchive',
    'MinecraftContentManager.importFile',
    'startContentImport(page)',
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    missing = [x for x in REQUIRED if x not in s]
    if MARKER not in s:
        missing.append(MARKER)
    if missing:
        raise SystemExit("[step342] missing contracts: " + ", ".join(missing))
    print("[step342] content install picker verification passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
