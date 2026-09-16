#!/usr/bin/env python3
"""Step 333: final generated-source authority before quality/Gradle.

Repairs semantic duplicate helpers and known Android generated-source regressions
introduced by late UI generators. Idempotent by construction.
"""
from pathlib import Path
import sys


def function_end(source: str, start: int) -> int:
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step333] missing body for function at {start}")
    depth = 0
    in_string = False
    in_triple = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    i = brace
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        nxt2 = source[i + 2] if i + 2 < len(source) else ""
        if in_line_comment:
            if ch == "\n": in_line_comment = False
            i += 1; continue
        if in_block_comment:
            if ch == "*" and nxt == "/": in_block_comment = False; i += 2; continue
            i += 1; continue
        if in_triple:
            if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = False; i += 3; continue
            i += 1; continue
        if in_string:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
            i += 1; continue
        if in_char:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == "'": in_char = False
            i += 1; continue
        if ch == "/" and nxt == "/": in_line_comment = True; i += 2; continue
        if ch == "/" and nxt == "*": in_block_comment = True; i += 2; continue
        if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = True; i += 3; continue
        if ch == '"': in_string = True; i += 1; continue
        if ch == "'": in_char = True; i += 1; continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                j = i + 1
                while j < len(source) and source[j] in "\r\n": j += 1
                return j
        i += 1
    raise SystemExit("[step333] unterminated function body")


def dedupe_signature(source: str, signature: str) -> tuple[str, int]:
    starts = []
    offset = 0
    while True:
        pos = source.find(signature, offset)
        if pos < 0: break
        starts.append(pos); offset = pos + 1
    if len(starts) <= 1:
        return source, 0
    removed = 0
    for pos in reversed(starts[1:]):
        end = function_end(source, pos)
        source = source[:pos] + source[end:]
        removed += 1
    return source, removed


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not path.is_file():
        raise SystemExit(f"[step333] missing UI source: {path}")
    source = path.read_text(encoding="utf-8")

    source = source.replace("this@DroidLauncherUiActivity.text", "primaryText")
    source = source.replace("setTextColor(text)", "setTextColor(primaryText)")
    source = source.replace("singleLine = true", "isSingleLine = true")
    source = source.replace("setSingleLine(true)", "isSingleLine = true")

    signatures = (
        "private fun serverPrefs(): android.content.SharedPreferences",
        "private fun getSavedServers(): List<Pair<String, Int>>",
        "private fun getServerName(index: Int): String",
        "private fun getServerStatus(host: String, port: Int): String",
        "private fun selectServer(host: String, port: Int)",
        "private fun deleteServer(index: Int)",
        "private fun showServerDialog(index: Int)",
        "private fun refreshServerStatus(host: String, port: Int)",
        "private fun selectedMinecraftVersion(): String",
        "private fun selectedMinecraftProfile(): String",
        "private fun saveMinecraftVersion(version: String)",
        "private fun saveMinecraftProfile(profile: String)",
        "private fun launchSelectedMinecraft()",
    )
    removed = 0
    for sig in signatures:
        source, count = dedupe_signature(source, sig)
        removed += count

    required_server = signatures[:8]
    missing = [sig for sig in required_server if sig not in source]
    if missing:
        raise SystemExit("[step333] required server contract missing: " + ", ".join(missing))
    duplicates = [sig for sig in signatures if source.count(sig) != 1]
    if duplicates:
        raise SystemExit("[step333] duplicate/missing critical helper: " + ", ".join(duplicates))
    forbidden = ("this@DroidLauncherUiActivity.text", "setTextColor(text)", "singleLine = true", "setSingleLine(true)")
    stale = [token for token in forbidden if token in source]
    if stale:
        raise SystemExit("[step333] stale generated Android token remains: " + ", ".join(stale))

    path.write_text(source, encoding="utf-8")
    print(f"[step333] final generated source authority applied; removed_duplicates={removed}")
    print("[step333] server helper ownership normalized to exactly one implementation")
    print("[step333] Android text-color and EditText APIs canonicalized")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
