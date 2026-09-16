#!/usr/bin/env python3
"""Final compile-boundary repair for the generated launcher UI.

Runs after all late UI generators. Restores Java resolver helpers, repairs known
multiline joinToString corruption, and normalizes any ordinary quoted Kotlin
string that a generator accidentally split across a physical newline.
"""
from pathlib import Path
import re
import sys

HELPERS = '''    private fun recommendedJavaForVersion(version: String): Int {
        val nums = version.split('.').mapNotNull { it.toIntOrNull() }
        val major = nums.getOrNull(0) ?: return 17
        val minor = nums.getOrNull(1) ?: 0
        val patch = nums.getOrNull(2) ?: 0
        return when {
            major == 1 && minor <= 16 -> 8
            major == 1 && minor <= 19 -> 17
            major == 1 && minor == 20 && patch < 5 -> 17
            major == 1 && (minor > 20 || (minor == 20 && patch >= 5)) -> 21
            major >= 25 -> 25
            else -> 21
        }
    }

    private fun storedJavaOverride(): Int? {
        val raw = getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_java_runtime", "auto") ?: "auto"
        return raw.removePrefix("Internal-").toIntOrNull()
    }

    private fun resolveJavaForVersion(version: String): Int =
        storedJavaOverride() ?: recommendedJavaForVersion(version)

    private fun saveJavaOverride(value: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("selected_java_runtime", value)
            .apply()
        System.setProperty("droid.launcher.java.runtime", value)
    }

    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

'''

BLOCK_HELPERS = (
    '    private fun recommendedJavaForVersion(version: String): Int',
    '    private fun storedJavaOverride(): Int?',
    '    private fun saveJavaOverride(value: String)',
)
EXPRESSION_HELPERS = (
    '    private fun resolveJavaForVersion(version: String)',
    '    private fun getResolvedJavaForLaunch(version: String)',
)


def function_end(source: str, start: int) -> int:
    brace = source.find('{', start)
    if brace < 0:
        raise ValueError('missing function body')
    depth = 0
    in_string = in_triple = in_char = in_line = in_block = False
    escaped = False
    i = brace
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ''
        nxt2 = source[i + 2] if i + 2 < len(source) else ''
        if in_line:
            if ch == '\n': in_line = False
            i += 1; continue
        if in_block:
            if ch == '*' and nxt == '/': in_block = False; i += 2; continue
            i += 1; continue
        if in_triple:
            if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = False; i += 3; continue
            i += 1; continue
        if in_string:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == '"': in_string = False
            i += 1; continue
        if in_char:
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == "'": in_char = False
            i += 1; continue
        if ch == '/' and nxt == '/': in_line = True; i += 2; continue
        if ch == '/' and nxt == '*': in_block = True; i += 2; continue
        if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = True; i += 3; continue
        if ch == '"': in_string = True; i += 1; continue
        if ch == "'": in_char = True; i += 1; continue
        if ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unterminated function body')


def expression_end(source: str, start: int) -> int:
    line_end = source.find('\n', start)
    if line_end < 0:
        return len(source)
    return line_end + 1


def remove_function(source: str, signature: str, expression: bool) -> str:
    while True:
        start = source.find(signature)
        if start < 0:
            return source
        end = expression_end(source, start) if expression else function_end(source, start)
        while end < len(source) and source[end] in '\r\n':
            end += 1
        source = source[:start] + source[end:]


def restore_helpers(source: str) -> str:
    for sig in BLOCK_HELPERS:
        source = remove_function(source, sig, expression=False)
    for sig in EXPRESSION_HELPERS:
        source = remove_function(source, sig, expression=True)
    anchor = source.find('    private fun rendererPage() {')
    if anchor < 0:
        anchor = source.find('    private fun controlsPage() {')
    if anchor < 0:
        raise SystemExit('[step349] stable insertion anchor for Java helpers not found')
    return source[:anchor] + HELPERS + source[anchor:]


def repair_dependency_join(source: str) -> str:
    source = re.sub(
        r'names\.joinToString\("\s*\n\s*"\) \{ "• \$it" \}',
        'names.joinToString("\\n") { "• $it" }',
        source,
    )
    source = source.replace(
        'names.joinToString("\n") { "• $it" }',
        'names.joinToString("\\n") { "• $it" }',
    )
    return source


def repair_regular_string_newlines(source: str) -> tuple[str, int]:
    """Turn illegal ordinary quoted-string newlines into escaped \n sequences.

    Triple-quoted strings, comments, and character literals are left untouched.
    A second pass over the repaired result is used to prove no regular string
    remains split over a physical newline.
    """
    out: list[str] = []
    i = 0
    changed = 0
    in_line_comment = in_block_comment = False
    in_string = in_triple = in_char = False
    escaped = False
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ''
        nxt2 = source[i + 2] if i + 2 < len(source) else ''
        if in_line_comment:
            out.append(ch)
            if ch == '\n': in_line_comment = False
            i += 1; continue
        if in_block_comment:
            out.append(ch)
            if ch == '*' and nxt == '/': out.append('/'); i += 2; in_block_comment = False
            else: i += 1
            continue
        if in_triple:
            out.append(ch)
            if ch == '"' and nxt == '"' and nxt2 == '"': out.extend(['"', '"']); i += 3; in_triple = False
            else: i += 1
            continue
        if in_string:
            if escaped:
                out.append(ch); escaped = False; i += 1; continue
            if ch == '\\': out.append(ch); escaped = True; i += 1; continue
            if ch == '"': out.append(ch); i += 1; in_string = False; continue
            if ch == '\n':
                out.append('\\n'); changed += 1; i += 1
                while i < len(source) and source[i] in ' \t\r': i += 1
                continue
            out.append(ch); i += 1; continue
        if in_char:
            out.append(ch)
            if escaped: escaped = False
            elif ch == '\\': escaped = True
            elif ch == "'": in_char = False
            i += 1; continue
        if ch == '/' and nxt == '/': out.extend([ch, nxt]); i += 2; in_line_comment = True; continue
        if ch == '/' and nxt == '*': out.extend([ch, nxt]); i += 2; in_block_comment = True; continue
        if ch == '"' and nxt == '"' and nxt2 == '"': out.extend(['"', '"', '"']); i += 3; in_triple = True; continue
        if ch == '"': out.append(ch); i += 1; in_string = True; escaped = False; continue
        if ch == "'": out.append(ch); i += 1; in_char = True; escaped = False; continue
        out.append(ch); i += 1
    if in_string:
        raise ValueError('unterminated regular Kotlin string literal')
    return ''.join(out), changed


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file():
        raise SystemExit(f'[step349] missing UI source: {ui}')
    source = ui.read_text(encoding='utf-8')
    before = source
    source = restore_helpers(source)
    source = repair_dependency_join(source)
    source, changed_strings = repair_regular_string_newlines(source)
    _, residual = repair_regular_string_newlines(source)
    if residual:
        raise SystemExit(f'[step357] residual regular-string newline count: {residual}')
    required = (
        'private fun recommendedJavaForVersion(version: String): Int',
        'private fun resolveJavaForVersion(version: String): Int',
        'private fun saveJavaOverride(value: String)',
        'names.joinToString("\\n") { "• $it" }',
    )
    for needle in required:
        if needle not in source:
            raise SystemExit(f'[step349] missing post-repair contract: {needle}')
    ui.write_text(source, encoding='utf-8')
    print(f'[step357] generated regular Kotlin string repair count={changed_strings}; changed={int(source != before)}')
    print('[step349] Java resolver helpers restored after all late UI rewrites')
    print('[step349] dependency joinToString escaped safely')
    print('[step357] no remaining multiline regular Kotlin strings')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
