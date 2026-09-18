#!/usr/bin/env python3
"""Step 431: remove the obsolete fake first-run bootstrap gate from generated UI.

The current Droid Launcher contract prepares required components through the real
runtime/install managers and must open the production Game page directly.
This repair is idempotent and removes only the legacy bootstrap UI/state block.
"""
from pathlib import Path
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
FORBIDDEN = (
    "showBootstrapGate",
    "bootstrapComplete",
    "extractBootstrapComponents",
    "BootstrapComponent",
    "bootstrapComponents",
    "droid_launcher_bootstrap",
    "components_extracted",
)

def method_end(text: str, start: int) -> int:
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit("[step431] method opening brace missing")
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ""
        n2 = text[i + 2] if i + 2 < len(text) else ""
        if state == "line":
            if c == "\n": state = "code"
            i += 1; continue
        if state == "block":
            if c == "*" and n == "/": state = "code"; i += 2
            else: i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"': state = "code"; i += 3
            else: i += 1
            continue
        if state == "string":
            if escaped: escaped = False
            elif c == "\\": escaped = True
            elif c == '"': state = "code"
            i += 1; continue
        if state == "char":
            if escaped: escaped = False
            elif c == "\\": escaped = True
            elif c == "'": state = "code"
            i += 1; continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = "triple"; i += 3; continue
        if c == '"': state = "string"; i += 1; continue
        if c == "'": state = "char"; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise SystemExit("[step431] unterminated method")

def replace_on_create(text: str) -> str:
    marker = "    override fun onCreate("
    start = text.find(marker)
    if start < 0:
        raise SystemExit("[step431] onCreate not found")
    end = method_end(text, start)
    replacement = """    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        buildUi()
        showPage("Game")
    }"""
    return text[:start] + replacement + text[end:]

def remove_method_if_present(text: str, signature: str) -> str:
    while True:
        start = text.find(signature)
        if start < 0:
            return text
        return text[:start] + text[method_end(text, start):]

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    matches = list((root / "app/src/main/java").rglob(UI_REL.name))
    if len(matches) != 1:
        raise SystemExit(f"[step431] expected exactly one {UI_REL.name}, found {len(matches)}")
    path = matches[0]
    source = path.read_text(encoding="utf-8")

    source = replace_on_create(source)

    block_start = source.find("\n    private data class BootstrapComponent")
    gate_start = source.find("\n    private fun showBootstrapGate()", max(block_start, 0))
    if block_start >= 0 and gate_start >= 0:
        gate_end = method_end(source, gate_start)
        source = source[:block_start] + source[gate_end:]

    for signature in (
        "    private fun showBootstrapGate(",
        "    private fun extractBootstrapComponents(",
        "    private fun bootstrapComplete(",
    ):
        source = remove_method_if_present(source, signature)

    lines = source.splitlines()
    cleaned = []
    for line in lines:
        if any(token in line for token in FORBIDDEN):
            continue
        cleaned.append(line)
    source = "\n".join(cleaned) + ("\n" if source.endswith("\n") else "")

    source = replace_on_create(source)
    leftovers = [token for token in FORBIDDEN if token in source]
    if leftovers:
        raise SystemExit("[step431] legacy bootstrap refs remain: " + ", ".join(leftovers))
    if 'buildUi()\n        showPage("Game")' not in source:
        raise SystemExit("[step431] direct Game startup contract missing")
    path.write_text(source, encoding="utf-8")
    print("[step431] obsolete fake bootstrap gate removed; direct Game startup is authoritative")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
