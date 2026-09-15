#!/usr/bin/env python3
"""Step 295: restore Feature Center navigation after the final Home/Account UI replacement.

Keeps the first-run bootstrap gate isolated while making Features reachable from
normal launcher navigation. The repair is idempotent and source-only.
"""
from pathlib import Path
import sys


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step295] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step295] opening brace not found: {signature}")
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
    raise SystemExit(f"[step295] unterminated method: {signature}")


def replace_method(source: str, signature: str, replacement: str) -> str:
    start, end = method_block(source, signature)
    return source[:start] + replacement + source[end:]


def patch_show_page(source: str) -> str:
    if '"Features" -> featuresPage()' in source:
        return source
    start, end = method_block(source, "    private fun showPage(page: String)")
    block = source[start:end]
    anchors = [
        '            "Controls" -> controlsPage()',
        '            "Renderer" -> rendererPage()',
        '            "Java" -> javaPage()',
    ]
    for anchor in anchors:
        if anchor in block:
            block = block.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
            return source[:start] + block + source[end:]
    raise SystemExit("[step295] no safe showPage anchor found")


def patch_build_ui(source: str) -> str:
    if 'setOnClickListener { showPage("Features") }' in source:
        return source
    start, end = method_block(source, "    private fun buildUi()")
    block = source[start:end]
    anchor = '        val settings = button("⚙")\n'
    if anchor not in block:
        raise SystemExit("[step295] settings navigation anchor missing")
    insertion = '''        // "✦" to "Features"
        val features = button("✦")
        features.setOnClickListener { showPage("Features") }
'''
    block = block.replace(anchor, insertion + anchor, 1)
    old_list = '        listOf(home, accounts, downloads, settings).forEach {\n'
    if old_list not in block:
        raise SystemExit("[step295] navigation list anchor missing")
    block = block.replace(old_list, '        listOf(home, accounts, downloads, features, settings).forEach {\n', 1)
    return source[:start] + block + source[end:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step295] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    if "private fun featuresPage()" not in source:
        raise SystemExit("[step295] Feature Center page implementation is missing")
    source = patch_show_page(source)
    source = patch_build_ui(source)
    if '"Features" -> featuresPage()' not in source:
        raise SystemExit('[step295] Feature Center case still missing')
    if 'setOnClickListener { showPage("Features") }' not in source:
        raise SystemExit('[step295] Feature Center button handler still missing')
    ui.write_text(source, encoding="utf-8")
    print('[step295] Feature Center navigation restored')
    print('[step295] normal launcher shell exposes a dedicated ✦ Features button')
    print('[step295] first-run bootstrap gate remains navigation-free until installation completes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
