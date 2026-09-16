#!/usr/bin/env python3
"""Step 297/298: normalize generated Android EditText single-line APIs."""
from pathlib import Path
import re
import sys

TOKEN = re.compile(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step297] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    token_replacements = len(TOKEN.findall(source))
    repaired = TOKEN.sub("isSingleLine", source)
    setter_replacements = repaired.count("setSingleLine(true)")
    repaired = repaired.replace("setSingleLine(true)", "isSingleLine = true")
    ui.write_text(repaired, encoding="utf-8")
    if TOKEN.search(repaired) or "setSingleLine(true)" in repaired:
        raise SystemExit("[step297] unresolved EditText single-line API remains")
    print(f"[step297] EditText single-line normalization complete; property replacements={token_replacements}; setter replacements={setter_replacements}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
