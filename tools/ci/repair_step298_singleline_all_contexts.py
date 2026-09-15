#!/usr/bin/env python3
"""Step 298: repair every exact Kotlin `singleLine` property token in generated UI.

The generated Android View UI must use `isSingleLine`. This deliberately matches
only the exact camel-case token, so APIs such as setSingleLine(...) remain intact.
"""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step298] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    # Exact token only. Preserve setSingleLine()/isSingleLine untouched.
    repaired = re.sub(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])", "isSingleLine", source)
    ui.write_text(repaired, encoding="utf-8")
    leftovers = re.findall(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])", repaired)
    if leftovers:
        raise SystemExit("[step298] unresolved exact singleLine tokens remain")
    print(f"[step298] exact singleLine token repair complete; replacements={source.count('singleLine') - repaired.count('singleLine')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
