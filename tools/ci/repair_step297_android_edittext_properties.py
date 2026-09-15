#!/usr/bin/env python3
"""Step 297/298: repair every exact Kotlin `singleLine` property token in generated UI.

Generated Android View code uses `isSingleLine`. Only the exact camel-case
property token is rewritten; API names such as setSingleLine(...) remain valid.
"""
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
    replacements = len(TOKEN.findall(source))
    repaired = TOKEN.sub("isSingleLine", source)
    ui.write_text(repaired, encoding="utf-8")
    if TOKEN.search(repaired):
        raise SystemExit("[step297] unresolved exact singleLine tokens remain")
    print(f"[step297] exact singleLine property repair complete; replacements={replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
