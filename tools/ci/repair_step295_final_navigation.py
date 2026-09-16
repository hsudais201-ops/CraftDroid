#!/usr/bin/env python3
"""Step 295: restore Feature Center navigation after generated UI replacement.

Variant-tolerant, idempotent final navigation repair. If the current generated
launcher already has a Features rail entry, its generic handler is made explicit
instead of creating a duplicate button.
"""
from pathlib import Path
import re
import sys


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step295] method not found: {signature}")
    brace = source.find('{', start)
    if brace < 0:
        raise SystemExit(f"[step295] opening brace not found: {signature}")
    depth = 0
    quoted = triple = False
    escaped = False
    i = brace
    while i < len(source):
        ch = source[i]
        n = source[i + 1] if i + 1 < len(source) else ''
        n2 = source[i + 2] if i + 2 < len(source) else ''
        if triple:
            if ch == '"' and n == '"' and n2 == '"': triple = False; i += 3
            else: i += 1
            continue
        if quoted:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': quoted = False
            i += 1
            continue
        if ch == '"' and n == '"' and n2 == '"': triple = True; i += 3; continue
        if ch == '"': quoted = True; i += 1; continue
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: return start, i + 1
        i += 1
    raise SystemExit(f"[step295] unterminated method: {signature}")


def patch_show_page(source: str) -> str:
    if '"Features" -> featuresPage()' in source:
        return source
    start, end = method_block(source, "    private fun showPage(page: String)")
    block = source[start:end]
    for anchor in (
        '            "Controls" -> controlsPage()',
        '            "Renderer" -> rendererPage()',
        '            "Java" -> javaPage()',
        '            "Library" -> libraryPage()',
        '            "About" -> aboutPage()',
    ):
        if anchor in block:
            block = block.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
            return source[:start] + block + source[end:]
    match = re.search(r'(?m)^\s*else\s*->\s*\{?', block)
    if match:
        block = block[:match.start()] + '            "Features" -> featuresPage()\n' + block[match.start():]
        return source[:start] + block + source[end:]
    raise SystemExit("[step295] no safe showPage anchor found")


def make_feature_button() -> str:
    return '''        val features = button("✦").apply {
            contentDescription = "Features - Feature Center"
            setOnClickListener { showPage("Features") }
        }
'''


def patch_build_ui(source: str) -> str:
    if 'setOnClickListener { showPage("Features") }' in source:
        return source
    start, end = method_block(source, "    private fun buildUi()")
    block = source[start:end]

    # Current generator variant: Features already exists in the rail, but is routed
    # through showPage(page). Make only that path explicit and keep every other page
    # on the generic handler.
    if '"✦" to "Features"' in block and 'b.setOnClickListener { showPage(page) }' in block:
        block = block.replace(
            '            b.setOnClickListener { showPage(page) }',
            '            if (page == "Features") b.setOnClickListener { showPage("Features") } else b.setOnClickListener { showPage(page) }',
            1,
        )
        return source[:start] + block + source[end:]

    settings_decl = re.search(r'(?m)^\s*val\s+settings\s*=\s*button\([^\n]*\)\s*$', block)
    if settings_decl:
        block = block[:settings_decl.start()] + make_feature_button() + block[settings_decl.start():]
        nav = re.search(r'(?m)^(\s*)listOf\(([^\n]*\bsettings\b[^\n]*)\)\.forEach\s*\{', block)
        if nav and 'features' not in nav.group(2):
            block = block[:nav.start(2)] + nav.group(2).replace('settings', 'features, settings', 1) + block[nav.end(2):]
        return source[:start] + block + source[end:]

    nav = re.search(r'(?m)^(\s*)listOf\(([^\n]*(?:home|accounts|downloads)[^\n]*)\)\.forEach\s*\{', block)
    if nav:
        args = nav.group(2)
        if 'features' not in args:
            block = block[:nav.start(2)] + args.rstrip() + ', features' + block[nav.end(2):]
        block = block[:nav.start()] + make_feature_button() + block[nav.start():]
        return source[:start] + block + source[end:]

    raise SystemExit('[step295] unable to locate a safe navigation shell for Features')


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
    print('[step295] Feature Center navigation restored for generated UI variant')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
