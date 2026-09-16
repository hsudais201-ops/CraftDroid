#!/usr/bin/env python3
"""Final compile-boundary repair for the generated launcher UI.

Runs after all late UI generators. Restores Java resolver helpers if a late page
replacement removed them and repairs the known multiline joinToString corruption.
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


def remove_all_functions(source: str, signature: str) -> str:
    while True:
        start = source.find(signature)
        if start < 0:
            return source
        end = function_end(source, start)
        while end < len(source) and source[end] in '\r\n':
            end += 1
        source = source[:start] + source[end:]


def restore_helpers(source: str) -> str:
    for sig in (
        '    private fun recommendedJavaForVersion(version: String): Int',
        '    private fun storedJavaOverride(): Int?',
        '    private fun resolveJavaForVersion(version: String): Int',
        '    private fun saveJavaOverride(value: String)',
        '    private fun getResolvedJavaForLaunch(version: String): Int',
    ):
        source = remove_all_functions(source, sig)
    anchor = source.find('    private fun rendererPage() {')
    if anchor < 0:
        anchor = source.find('    private fun controlsPage() {')
    if anchor < 0:
        raise SystemExit('[step349] stable insertion anchor for Java helpers not found')
    return source[:anchor] + HELPERS + source[anchor:]


def repair_dependency_join(source: str) -> str:
    # Repair both literal newline variants produced by generated Python templates.
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file():
        raise SystemExit(f'[step349] missing UI source: {ui}')
    source = ui.read_text(encoding='utf-8')
    before = source
    source = restore_helpers(source)
    source = repair_dependency_join(source)
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
    print(f'[step349] final generated UI compile repair applied; changed={int(source != before)}')
    print('[step349] Java resolver helpers restored after all late UI rewrites')
    print('[step349] required dependency joinToString escaped safely')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
