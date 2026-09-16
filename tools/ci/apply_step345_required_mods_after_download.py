#!/usr/bin/env python3
"""Step 345: show required mod/dependency information after modpack downloads."""
from pathlib import Path
import re
import sys

MARKER = "// STEP345_REQUIRED_MODS_AFTER_DOWNLOAD"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step345] generated UI missing")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step345] required-mod flow already present")
        return 0

    # Step 344 uses DownloadManager and reports enqueue success inside a compact
    # runOnUiThread lambda. Match that real generated form rather than a brittle
    # exact indentation/string contract.
    pattern = re.compile(
        r'(?m)^(\s*)runOnUiThread \{ android\.widget\.Toast\.makeText\(this, "Download started: \$filename", android\.widget\.Toast\.LENGTH_LONG\)\.show\(\) \}$'
    )
    match = pattern.search(s)
    if not match:
        raise SystemExit("[step345] DownloadManager success toast anchor not found")

    indent = match.group(1)
    replacement = (
        match.group(0)
        + f'\n{indent}if (page == "Modpack") showRequiredModsForProject(slug, name)\n'
        + f'{indent}{MARKER}'
    )
    s = s[:match.start()] + replacement + s[match.end():]
    ui.write_text(s, encoding="utf-8")
    print("[step345] required-mod dialog is now shown after a modpack download")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
