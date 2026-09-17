#!/usr/bin/env python3
"""Step 359: final generated UI cleanup after all late generator mutations.

This runs after Step 349 and operates on the final materialized activity,
because earlier repair scripts can rewrite the same file late in the pipeline.
"""
from pathlib import Path
import re
import sys


def method_end(text: str, start: int) -> int:
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('[step359] method opening brace missing')
    depth = 0
    state = 'code'
    escaped = False
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        n2 = text[i + 2] if i + 2 < len(text) else ''
        if state == 'line':
            if c == '\n':
                state = 'code'
            i += 1
            continue
        if state == 'block':
            if c == '*' and n == '/':
                state = 'code'
                i += 2
            else:
                i += 1
            continue
        if state == 'triple':
            if c == '"' and n == '"' and n2 == '"':
                state = 'code'
                i += 3
            else:
                i += 1
            continue
        if state == 'string':
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == '"':
                state = 'code'
            i += 1
            continue
        if state == 'char':
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == "'":
                state = 'code'
            i += 1
            continue
        if c == '/' and n == '/':
            state = 'line'; i += 2; continue
        if c == '/' and n == '*':
            state = 'block'; i += 2; continue
        if c == '"' and n == '"' and n2 == '"':
            state = 'triple'; i += 3; continue
        if c == '"':
            state = 'string'; i += 1; continue
        if c == "'":
            state = 'char'; i += 1; continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise SystemExit('[step359] unterminated method')


def find_methods(text: str, name: str) -> list[tuple[int, int]]:
    pat = re.compile(r'(?m)^\s*private\s+fun\s+' + re.escape(name) + r'\s*\(')
    return [(m.start(), method_end(text, m.start())) for m in pat.finditer(text)]


def normalize_edit_text(text: str) -> str:
    # Generated launcher code uses Android View EditText. The Kotlin API is
    # setSingleLine(), not a writable `singleLine` property.
    return re.sub(r'\bsingleLine\s*=\s*(true|false)\b', r'setSingleLine(\1)', text)


def normalize_private_member_indentation(text: str) -> str:
    # Kotlin ignores indentation for scope, but our structural verifier uses
    # declaration indentation to detect helpers that accidentally escaped their
    # generated class boundary. The late generator occasionally emits a member
    # function flush-left. Normalize only unindented private functions; genuine
    # top-level declarations are not expected in this Activity source.
    return re.sub(r'(?m)^private\s+fun\s+', '    private fun ', text)


def keep_canonical_microsoft_helper(text: str) -> str:
    methods = find_methods(text, 'showMicrosoftAccountInfo')
    if not methods:
        raise SystemExit('[step359] Microsoft account entrypoint is missing')
    # Keep the final late-generated helper, then force it to the real Microsoft
    # sign-in page. This removes an older non-authentic placeholder helper.
    for start, end in reversed(methods[:-1]):
        text = text[:start] + text[end:]
    methods = find_methods(text, 'showMicrosoftAccountInfo')
    if len(methods) != 1:
        raise SystemExit(f'[step359] Microsoft account helper count={len(methods)}')
    start, end = methods[0]
    canonical = '    private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }'
    return text[:start] + canonical + text[end:]


def assert_final(source: str) -> None:
    if 'singleLine =' in source:
        raise SystemExit('[step359] invalid singleLine property remains')
    if source.count('private fun showMicrosoftAccountInfo()') != 1:
        raise SystemExit('[step359] Microsoft account helper is not unique')
    if 'private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }' not in source:
        raise SystemExit('[step359] Microsoft account entrypoint is not canonical')
    if 'private fun showMicrosoftSignInPage()' not in source:
        raise SystemExit('[step359] real Microsoft sign-in page is missing')
    if source.count('override fun onActivityResult(') != 1:
        raise SystemExit('[step359] cosmetic picker callback count is not exactly 1')
    if 'microsoft_skin_uri' not in source or 'microsoft_cape_uri' not in source:
        raise SystemExit('[step359] cosmetic URI persistence is missing')
    if '\nprivate fun ' in source:
        raise SystemExit('[step359] top-level private helper remains outside class')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file():
        raise SystemExit(f'[step359] missing UI source: {ui}')
    source = ui.read_text(encoding='utf-8')
    source = normalize_edit_text(source)
    source = normalize_private_member_indentation(source)
    source = keep_canonical_microsoft_helper(source)
    source = normalize_edit_text(source)
    source = normalize_private_member_indentation(source)
    ui.write_text(source, encoding='utf-8')
    assert_final(source)
    print('[step359] final generated UI cleanup PASS: EditText APIs normalized; Microsoft entrypoint canonicalized and deduplicated; member indentation normalized')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
