#!/usr/bin/env python3
"""Step 462 verifier."""
from pathlib import Path
import sys

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=root/"app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step462-verify] UI missing")
    s=ui.read_text(encoding="utf-8")
    for x in (
        "// STEP462_LOW_RAM_TOUCH_POLICY",
        "private fun step460CategoryCard(",
        "if (step376LowRam)",
        "action()",
        "animate().scaleX(0.97f)",
    ):
        if x not in s: raise SystemExit("[step462-verify] missing: "+x)
    if s.count("// STEP462_LOW_RAM_TOUCH_POLICY") != 1:
        raise SystemExit("[step462-verify] duplicate marker")
    print("[step462-verify] low-RAM touch policy verified")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
