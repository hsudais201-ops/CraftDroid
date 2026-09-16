#!/usr/bin/env python3
"""Step 351: repair the first-run component preparation ordering bug."""
from pathlib import Path
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
VERIFY = '                if (!bootstrapComplete()) throw java.io.IOException("Component preparation verification failed")'
PERSIST = '                bootstrapPrefs().edit().putBoolean("components_extracted", true).apply()'


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / UI_REL
    if not ui.is_file():
        raise SystemExit(f"[step351] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    gate = source.find("private fun extractBootstrapComponents")
    if gate < 0:
        raise SystemExit("[step351] extractBootstrapComponents() not found")

    verify_pos = source.find(VERIFY, gate)
    persist_pos = source.find(PERSIST, gate)
    if verify_pos < 0 or persist_pos < 0:
        raise SystemExit("[step351] component preparation state-machine markers not found")

    if persist_pos > verify_pos:
        source = source[:verify_pos] + PERSIST + "\n" + source[verify_pos:persist_pos] + source[persist_pos + len(PERSIST):]
        ui.write_text(source, encoding="utf-8")
        print("[step351] fixed component preparation ordering: persist success flag before verification")
    else:
        print("[step351] component preparation ordering already correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
