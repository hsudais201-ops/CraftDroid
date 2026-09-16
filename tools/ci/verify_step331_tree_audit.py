#!/usr/bin/env python3
"""Step 331: deterministic whole-tree static audit for generated Android source.

This is intentionally complementary to Gradle/Kotlin compilation: it catches
structural regressions introduced by the many source-generating repair stages.
"""
from __future__ import annotations
from pathlib import Path
import re
import subprocess
import sys

TEXT_EXTENSIONS = {".kt", ".java", ".xml", ".gradle", ".kts", ".properties", ".json", ".yml", ".yaml", ".py", ".sh", ".md"}
LEGACY = ("Za" + "lith", "ZALITH")
HTTP_EXEMPT = ("http://schemas.android.com/", "http://www.w3.org/", "http://auth.xboxlive.com")


def text_files(root: Path) -> list[Path]:
    return [p for p in sorted(root.rglob("*")) if p.is_file() and p.suffix.lower() in TEXT_EXTENSIONS and ".gradle" not in p.parts and "build" not in p.parts]


def brace_balance(text: str) -> int:
    depth = 0
    in_string = False
    triple = False
    escaped = False
    in_line_comment = False
    in_block_comment = False
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        nxt2 = text[i + 2] if i + 2 < len(text) else ""
        if in_line_comment:
            if ch == "\n": in_line_comment = False
        elif in_block_comment:
            if ch == "*" and nxt == "/": in_block_comment = False; i += 1
        elif triple:
            if ch == '"' and nxt == '"' and nxt2 == '"': triple = False; i += 2
        elif in_string:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
        elif ch == "/" and nxt == "/": in_line_comment = True; i += 1
        elif ch == "/" and nxt == "*": in_block_comment = True; i += 1
        elif ch == '"' and nxt == '"' and nxt2 == '"': triple = True; i += 2
        elif ch == '"': in_string = True
        elif ch == "{": depth += 1
        elif ch == "}": depth -= 1
        i += 1
    return depth


def check(root: Path) -> list[str]:
    errors: list[str] = []
    files = text_files(root)
    if len(files) < 20:
        errors.append(f"generated tree unexpectedly small: {len(files)} text files")
    main = root / "app/src/main/java/com/example/launcher"
    required = (
        "DroidLauncherUiActivity.kt",
        "MinecraftVersionInstallManager.kt",
        "MinecraftLatestVersionManager.kt",
        "MinecraftModpackManager.kt",
        "MinecraftContentManager.kt",
        "MinecraftLoaderProfile.kt",
        "MinecraftRuntimeProfile.kt",
        "LauncherBackgroundInstallController.kt",
        "DroidLauncherUpdateManager.kt",
    )
    for name in required:
        if not (main / name).is_file(): errors.append(f"missing required production source: {name}")

    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as exc:
            errors.append(f"non-UTF8 text file: {path}: {exc}")
            continue
        if any(token in text for token in LEGACY): errors.append(f"legacy branding remains: {path}")
        if path.suffix.lower() in {".kt", ".java"} and brace_balance(text) != 0:
            errors.append(f"unbalanced source braces: {path}")
        if path.suffix.lower() in {".kt", ".java"} and re.search(r"\b(?:TODO|FIXME|NotImplementedException)\b", text):
            errors.append(f"unfinished marker in production source: {path}")
        if path.suffix.lower() in {".kt", ".java"}:
            for m in re.finditer(r"http://[^\"'\s)]+", text, re.IGNORECASE):
                value = m.group(0).lower()
                if not value.startswith(HTTP_EXEMPT):
                    errors.append(f"plaintext HTTP endpoint in {path}: {m.group(0)}")
                    break

    # Exact declaration uniqueness for the critical classes/objects.
    for name in required:
        path = main / name
        if not path.is_file(): continue
        text = path.read_text(encoding="utf-8")
        stem = path.stem
        count = len(re.findall(rf"\b(?:object|class|interface)\s+{re.escape(stem)}\b", text))
        if count != 1:
            errors.append(f"{name}: expected one top-level {stem} declaration, found {count}")

    # Python repair scripts must stay syntactically valid.
    for py in sorted((root.parent / "tools/ci").glob("*.py")):
        try:
            result = subprocess.run([sys.executable, "-m", "py_compile", str(py)], capture_output=True, text=True)
        except OSError as exc:
            errors.append(f"could not execute py_compile for {py}: {exc}")
            continue
        if result.returncode:
            errors.append(f"Python syntax error in {py}: {result.stderr.strip()}")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    errors = check(root)
    if errors:
        for error in errors[:100]: print(f"[step331] FAIL {error}")
        return 1
    print("[step331] whole-tree structural audit passed")
    print("[step331] required runtime/content/update sources present")
    print("[step331] Kotlin/Java brace balance and critical declaration uniqueness passed")
    print("[step331] repair-script Python syntax audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
