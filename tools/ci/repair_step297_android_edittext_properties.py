#!/usr/bin/env python3
"""Step 297: repair Android TextView Kotlin property mappings in generated launcher UI.

The generated Java View based UI must use the Kotlin-mapped `isSingleLine`
property for android.widget.EditText/TextView. Compose `singleLine = true`
arguments elsewhere are intentionally untouched.
"""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step297] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    before = source
    # Only change bare assignments in this Android View activity. Compose
    # `singleLine = true` named arguments are in different files and remain valid.
    source = re.sub(r'(?<![A-Za-z0-9_])singleLine\s*=\s*true', 'isSingleLine = true', source)
    changed = source != before
    ui.write_text(source, encoding="utf-8")
    print(f"[step297] EditText isSingleLine mapping repaired: changed={int(changed)}")
    if re.search(r'(?m)^\s*singleLine\s*=\s*true\s*$', source):
        raise SystemExit("[step297] bare singleLine assignment still present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
