#!/usr/bin/env python3
"""Read-only post-mutation verifier for the final generated launcher UI."""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file():
        raise SystemExit(f'[step360] missing UI source: {ui}')
    source = ui.read_text(encoding='utf-8')
    bad_edit = re.search(r'\bsingleLine\s*=\s*(true|false)\b', source)
    if bad_edit:
        raise SystemExit(f'[step360] stale Android EditText singleLine property at offset {bad_edit.start()}')
    helper_count = len(re.findall(r'(?m)^\s*private\s+fun\s+showMicrosoftAccountInfo\s*\(', source))
    if helper_count != 1:
        raise SystemExit(f'[step360] expected exactly one Microsoft account helper, found {helper_count}')
    if 'private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }' not in source:
        raise SystemExit('[step360] Microsoft account entrypoint is not canonical')
    callback_count = len(re.findall(r'(?m)^\s*override\s+fun\s+onActivityResult\s*\(', source))
    if callback_count != 1:
        raise SystemExit(f'[step360] expected exactly one cosmetic picker callback, found {callback_count}')
    for marker in ('microsoft_skin_uri', 'microsoft_cape_uri', 'private fun showMicrosoftSignInPage()'):
        if marker not in source:
            raise SystemExit(f'[step360] required final UI marker missing: {marker}')
    print('[step360] read-only final generated UI verification PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
