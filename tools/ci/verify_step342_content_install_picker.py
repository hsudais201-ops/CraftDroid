#!/usr/bin/env python3
"""Verify real content import wiring for the Step 342 install buttons."""
from pathlib import Path
import sys

MARKER = "// STEP342_CONTENT_INSTALL_PICKER"
REQUIRED = [
    'Intent.ACTION_OPEN_DOCUMENT',
    'CONTENT_PICKER_REQUEST',
    'private var pendingContentPage: String?',
    'MinecraftContentManager.Kind.MODPACK',
    'MinecraftContentManager.Kind.MOD',
    'MinecraftContentManager.Kind.SHADER',
    'MinecraftContentManager.Kind.RESOURCE_PACK',
    'MinecraftContentManager.importArchive',
    'MinecraftContentManager.importFile',
    'private fun startContentImport(pageName: String)',
]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Accept both valid Android/Kotlin spellings. Step 342 intentionally uses the
    # fully-qualified type to remain independent of import ordering in generated UI.
    result_callback_ok = (
        'override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?)' in s
        or 'override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?)' in s
    )
    required = list(REQUIRED)
    if not result_callback_ok:
        required.append('override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) or android.content.Intent?')

    missing = [x for x in required if x not in s]
    if MARKER not in s:
        missing.append(MARKER)
    if missing:
        raise SystemExit("[step342] missing contracts: " + ", ".join(missing))
    print("[step342] content install picker verification passed")
    print("[step342] callback accepts imported or fully-qualified android.content.Intent")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
