#!/usr/bin/env python3
"""Step 292: repair generated UI after the first-run gate is applied.

The historical UI generators use several different onCreate signatures. Keep
exactly one onCreate and make all generated text-color references point at the
actual primaryText property. This runs before the source verifier and never
removes the bootstrap gate.
"""
from pathlib import Path
import sys


def method_block(source: str, start: int) -> tuple[int, int]:
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit("[step292] onCreate opening brace missing")
    depth = 0
    quoted = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit("[step292] unterminated onCreate")


def repair_on_create(source: str) -> str:
    signatures = []
    cursor = 0
    needle = "    override fun onCreate("
    while True:
        pos = source.find(needle, cursor)
        if pos < 0:
            break
        end = source.find(") {", pos)
        if end < 0:
            raise SystemExit("[step292] malformed onCreate signature")
        signatures.append((pos, end + 3))
        cursor = end + 3
    if len(signatures) <= 1:
        return source

    # Keep the last declaration because Step 287's bootstrap-aware onCreate is
    # intentionally the authoritative one.
    ranges = []
    for pos, _ in signatures[:-1]:
        start, end = method_block(source, pos)
        ranges.append((start, end))
    for start, end in reversed(ranges):
        source = source[:start] + source[end:]
    return source


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step292] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    if "private fun showBootstrapGate()" not in source:
        raise SystemExit("[step292] first-run bootstrap gate is missing")
    source = repair_on_create(source)
    source = source.replace("setTextColor(this@DroidLauncherUiActivity.text)", "setTextColor(primaryText)")
    source = source.replace("setTextColor(text)", "setTextColor(primaryText)")
    ui.write_text(source, encoding="utf-8")
    print("[step292] first-run gate compile repair complete")
    print("[step292] exactly one onCreate retained; bootstrap-aware declaration is authoritative")
    print("[step292] generated text colors use primaryText")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
