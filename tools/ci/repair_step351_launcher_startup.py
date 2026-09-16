#!/usr/bin/env python3
"""Make launcher startup deterministic and remove the fake bootstrap gate."""
from pathlib import Path
import sys


def method_end(text: str, start: int) -> int:
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('[step351] onCreate opening brace missing')
    depth = 0
    state = 'code'
    escaped = False
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        n2 = text[i + 2] if i + 2 < len(text) else ''
        if state == 'line':
            if c == '\n': state = 'code'
            i += 1; continue
        if state == 'block':
            if c == '*' and n == '/': state = 'code'; i += 2
            else: i += 1
            continue
        if state == 'triple':
            if c == '"' and n == '"' and n2 == '"': state = 'code'; i += 3
            else: i += 1
            continue
        if state == 'string':
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': state = 'code'
            i += 1; continue
        if state == 'char':
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == "'": state = 'code'
            i += 1; continue
        if c == '/' and n == '/': state = 'line'; i += 2; continue
        if c == '/' and n == '*': state = 'block'; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = 'triple'; i += 3; continue
        if c == '"': state = 'string'; i += 1; continue
        if c == "'": state = 'char'; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise SystemExit('[step351] unterminated onCreate')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src')
    candidates = list((root / 'app/src/main/java').rglob('DroidLauncherUiActivity.kt'))
    if len(candidates) != 1:
        raise SystemExit(f'[step351] expected one launcher UI source, found {len(candidates)}')
    path = candidates[0]
    text = path.read_text(encoding='utf-8')
    start = text.find('    override fun onCreate(')
    if start < 0:
        raise SystemExit('[step351] onCreate not found')
    end = method_end(text, start)
    replacement = '''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        buildUi()
        showPage("Game")
    }'''
    text = text[:start] + replacement + text[end:]
    forbidden_calls = ['showBootstrapGate()']
    # A call may remain in dead legacy code, but startup must never invoke it.
    if 'showBootstrapGate()' in text[start:start + len(replacement) + 20]:
        raise SystemExit('[step351] fake bootstrap gate still referenced by onCreate')
    if 'buildUi()\n        showPage("Game")' not in text[start:start + 500]:
        raise SystemExit('[step351] direct Game startup not installed')
    path.write_text(text, encoding='utf-8')
    print('[step351] onCreate now opens Droid Launcher Game page directly in landscape mode')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
