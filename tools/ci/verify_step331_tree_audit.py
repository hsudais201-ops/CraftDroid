#!/usr/bin/env python3
"""Step 331: deterministic whole-tree static audit for generated Android source."""
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


def balance_source(text: str) -> int:
    """Count braces while correctly ignoring strings, char literals and comments."""
    depth = 0
    i = 0
    state = "code"
    escaped = False
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        nxt2 = text[i + 2] if i + 2 < len(text) else ""
        if state == "line_comment":
            if ch == "\n": state = "code"
        elif state == "block_comment":
            if ch == "*" and nxt == "/": state = "code"; i += 1
        elif state == "string":
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': state = "code"
        elif state == "triple":
            if ch == '"' and nxt == '"' and nxt2 == '"': state = "code"; i += 2
        elif state == "char":
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == "'": state = "code"
        elif ch == "/" and nxt == "/": state = "line_comment"; i += 1
        elif ch == "/" and nxt == "*": state = "block_comment"; i += 1
        elif ch == '"' and nxt == '"' and nxt2 == '"': state = "triple"; i += 2
        elif ch == '"': state = "string"
        elif ch == "'": state = "char"
        elif ch == "{": depth += 1
        elif ch == "}": depth -= 1
        i += 1
    return depth


def normalize_test_fixtures(root: Path) -> None:
    # A dummy test URL is a fixture, not a network transport endpoint. Prefer the
    # reserved HTTPS .invalid domain so the generated test tree is transport-safe.
    for path in text_files(root):
        if ".test." not in path.name and "src/test" not in path.as_posix():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        updated = text.replace("http://dummy", "https://dummy.invalid")
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            print(f"[step331] normalized dummy HTTP test fixture: {path}")


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
        if path.suffix.lower() in {".kt", ".java"} and balance_source(text) != 0:
            errors.append(f"unbalanced source braces: {path}")
        if path.suffix.lower() in {".kt", ".java"} and re.search(r"\b(?:TODO|FIXME|NotImplementedException)\b", text):
            errors.append(f"unfinished marker in source: {path}")
        if path.suffix.lower() in {".kt", ".java"}:
            for m in re.finditer(r"http://[^\"'\s)]+", text, re.IGNORECASE):
                value = m.group(0).lower()
                if not value.startswith(HTTP_EXEMPT):
                    errors.append(f"plaintext HTTP endpoint in {path}: {m.group(0)}")
                    break
    for name in required:
        path = main / name
        if not path.is_file(): continue
        text = path.read_text(encoding="utf-8")
        stem = path.stem
        count = len(re.findall(rf"\b(?:object|class|interface)\s+{re.escape(stem)}\b", text))
        if count != 1: errors.append(f"{name}: expected one top-level {stem} declaration, found {count}")
    for py in sorted((root.parent / "tools/ci").glob("*.py")):
        try:
            result = subprocess.run([sys.executable, "-m", "py_compile", str(py)], capture_output=True, text=True)
        except OSError as exc:
            errors.append(f"could not execute py_compile for {py}: {exc}")
            continue
        if result.returncode: errors.append(f"Python syntax error in {py}: {result.stderr.strip()}")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    normalize_test_fixtures(root)
    errors = check(root)
    if errors:
        for error in errors[:100]: print(f"[step331] FAIL {error}")
        return 1
    print("[step331] whole-tree structural audit passed")
    print("[step331] required runtime/content/update sources present")
    print("[step331] Kotlin/Java brace balance handles strings, chars and comments")
    print("[step331] HTTP, branding, unfinished-marker and Python syntax audits passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
