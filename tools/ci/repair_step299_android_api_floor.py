#!/usr/bin/env python3
"""Align the generated Android app API floor with the Java APIs it uses.

The launcher currently relies on java.nio.file and java.time APIs that are
platform APIs from Android API 26 onward. Keeping minSdk below that level
causes Android Lint's NewApi detector to reject the build and would risk
runtime failures on unsupported older Android releases. This pass is
idempotent and makes the generated build contract explicit.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    gradle = root / "app/build.gradle.kts"
    if not gradle.is_file():
        raise SystemExit(f"[step299] app build file not found: {gradle}")

    source = gradle.read_text(encoding="utf-8")
    updated, count = re.subn(r"(?m)^(\s*)minSdk\s*=\s*\d+\s*$", r"\1minSdk = 26", source)
    if count == 0:
        raise SystemExit("[step299] minSdk declaration not found")
    if "minSdk = 26" not in updated:
        raise SystemExit("[step299] minSdk normalization failed")

    gradle.write_text(updated, encoding="utf-8")
    print(f"[step299] Android API floor normalized to 26; replacements={count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
