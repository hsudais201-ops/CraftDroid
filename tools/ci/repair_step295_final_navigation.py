#!/usr/bin/env python3
"""Step 295: restore Feature Center navigation after generated UI replacement.

The generated launcher has had several navigation-shell variants. This repair is
therefore deliberately variant-tolerant and idempotent rather than depending on
one exact icon/text anchor.
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
    quoted = False
    triple = False
    escaped = False
    i = brace
    while i < len(source):
        ch = source[i]
        n = source[i + 1] if i + 1 < len(source) else ''
        n2 = source[i + 2] if i + 2 < len(source) else ''
        if triple:
            if ch == '"' and n == '"' and n2 == '"':
                triple = False
                i += 3
            else:
                i += 1
            continue
        if quoted:
            if escaped:
                escaped = False
            elif ch == '\\':
                escaped = True
            elif ch == '"':
                quoted = False
            i += 1
            continue
        if ch == '"' and n == '"' and n2 == '"':
            triple = True
            i += 3
            continue
        if ch == '"':
            quoted = True
            i += 1
            continue
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
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
        '            "Library" -> libraryPage()',
        '            "About" -> aboutPage()',
    ]
    for anchor in anchors:
        if anchor in block:
            block = block.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
            return source[:start] + block + source[end:]
    # Last safe case: insert immediately before an else arm in the page switch.
    match = re.search(r'(?m)^\s*else\s*->\s*\{?', block)
    if match:
        insertion = '            "Features" -> featuresPage()\n'
        block = block[:match.start()] + insertion + block[match.start():]
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
    feature_button = make_feature_button()

    # Variant A: original shell with a named settings button and navigation list.
    settings_decl = re.search(r'(?m)^\s*val\s+(settings)\s*=\s*button\([^\n]*\)\s*$', block)
    if settings_decl:
        insertion_at = settings_decl.start()
        block = block[:insertion_at] + feature_button + block[insertion_at:]
        nav = re.search(r'(?m)^(\s*)listOf\(([^\n]*\bsettings\b[^\n]*)\)\.forEach\s*\{', block)
        if nav:
            args = nav.group(2)
            if 'features' not in args:
                new_args = args.replace('settings', 'features, settings', 1)
                block = block[:nav.start(2)] + new_args + block[nav.end(2):]
            return source[:start] + block + source[end:]
        # Named settings exists even when the nav list was renamed; add the feature
        # control beside the other top-level buttons and keep it reachable.
        return source[:start] + block + source[end:]

    # Variant B: find any navigation list containing home/accounts/downloads.
    nav = re.search(
        r'(?m)^(\s*)listOf\(([^\n]*(?:home|accounts|downloads)[^\n]*)\)\.forEach\s*\{',
        block,
    )
    if nav:
        args = nav.group(2)
        if 'features' not in args:
            new_args = args.rstrip() + ', features'
            block = block[:nav.start(2)] + new_args + block[nav.end(2):]
        # Define the control immediately before the nav list so it is in scope.
        block = block[:nav.start()] + feature_button + block[nav.start():]
        return source[:start] + block + source[end:]

    # Variant C: any listOf(<button vars>) nav container.
    nav = re.search(r'(?m)^(\s*)listOf\(([^\n]+)\)\.forEach\s*\{', block)
    if nav and any(name in nav.group(2) for name in ('home', 'accounts', 'settings', 'downloads', 'server')):
        args = nav.group(2)
        if 'features' not in args:
            block = block[:nav.start(2)] + args.rstrip() + ', features' + block[nav.end(2):]
        block = block[:nav.start()] + feature_button + block[nav.start():]
        return source[:start] + block + source[end:]

    # Variant D: no reusable list. Use an existing settings/page navigation button
    # callback as the safest insertion point instead of fabricating a new container.
    callback = re.search(r'(?m)^\s*[^\n]*setOnClickListener\s*\{\s*showPage\("(?:Settings|Downloads|Accounts|Game)"\)\s*\}\s*$', block)
    if callback:
        block = block[:callback.end()] + '\n' + feature_button.rstrip() + '\n' + block[callback.end():]
        return source[:start] + block + source[end:]

    # No known navigation shell exists. Fail closed instead of creating an unreachable
    # UI object, so a generated-source change cannot silently satisfy the audit.
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
    print('[step295] first-run bootstrap behavior remains isolated from normal navigation')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
