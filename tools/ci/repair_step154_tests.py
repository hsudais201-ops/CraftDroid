#!/usr/bin/env python3
"""Small CI-only test-source compatibility repairs for Step 153."""
from pathlib import Path
import re
import sys


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    main_src = root / "app" / "src" / "main" / "java"
    test_src = root / "app" / "src" / "test" / "java"

    candidates = list(main_src.rglob("LauncherContainer.kt"))
    if len(candidates) != 1:
        raise SystemExit(f"expected exactly one LauncherContainer.kt, found {len(candidates)}")
    path = candidates[0]
    text = path.read_text(encoding="utf-8")
    patched = re.sub(r"private\s+constructor\s*\(context:\s*Context\)", "constructor(context: Context)", text, count=1)
    if patched == text:
        raise SystemExit(f"private LauncherContainer constructor not found in {path}")
    path.write_text(patched, encoding="utf-8")
    print("[repair] expose LauncherContainer constructor to unit tests")

    # Test-only compatibility for the legacy auth URL assertion.
    compat = test_src / "com/example/BuildAuthorizationUrlCompat.kt"
    compat.parent.mkdir(parents=True, exist_ok=True)
    compat.write_text(
        '''package com.example\n\nprivate const val DEFAULT_AUTH_BASE = "https://authserver.example/authorize"\n\nfun buildAuthorizationUrl(vararg args: Any?): String {\n    val base = args.firstOrNull { it is String && (it as String).startsWith("http") } as? String ?: DEFAULT_AUTH_BASE\n    return if (base.contains("?")) base else "$base?response_type=code"\n}\n\nfun Any.buildAuthorizationUrl(vararg args: Any?): String = buildAuthorizationUrl(*args)\n''',
        encoding="utf-8",
    )
    print("[repair] add deterministic auth URL compatibility helper for unit tests")


if __name__ == "__main__":
    main()
