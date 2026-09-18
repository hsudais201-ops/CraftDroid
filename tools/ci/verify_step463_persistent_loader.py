#!/usr/bin/env python3
"""Step 463 verifier."""
from pathlib import Path
import sys

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=root/"app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step463-verify] UI missing")
    s=ui.read_text(encoding="utf-8")
    required=(
        "// STEP463_PERSISTENT_LOADER_SELECTOR",
        "private fun step463LoaderPrefs()",
        "private fun step463LoaderKey(): String",
        "private fun step463SelectedLoader(): String",
        "private fun step463SelectLoader()",
        "setSingleChoiceItems(choices",
        'putString(step463LoaderKey(), value)',
        'step463SelectLoader()',
        "Vanilla", "Fabric", "Forge", "NeoForge", "Quilt"
    )
    for x in required:
        if x not in s: raise SystemExit("[step463-verify] missing: "+x)
    if s.count("private fun step463SelectLoader()") != 1:
        raise SystemExit("[step463-verify] duplicate loader selector")
    if s.count("private fun step463SelectedLoader(): String") != 1:
        raise SystemExit("[step463-verify] duplicate loader-state helper")
    print("[step463-verify] persistent per-instance loader selector verified")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
