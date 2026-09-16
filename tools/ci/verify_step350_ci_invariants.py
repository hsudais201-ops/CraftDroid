#!/usr/bin/env python3
"""Step 350: validate the authoritative build workflow cannot silently skip APK gates."""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    workflow = root / '.github/workflows/step257-resilient-build.yml'
    if not workflow.is_file():
        raise SystemExit('[step350] authoritative workflow missing')
    text = workflow.read_text(encoding='utf-8')
    required = [
        "gradle-version: '9.6.0'",
        'validate-wrappers: false',
        ':app:lintDebug',
        ':app:testDebugUnitTest',
        ':app:assembleDebug',
        'aapt2 dump badging',
        'apksigner verify --verbose',
        'zipalign -c -P 16 -v 4',
        'Droid-Launcher-Step257-debug',
        'Upload APK',
        'Verify Step349 regression harness',
    ]
    for needle in required:
        if needle not in text:
            raise SystemExit(f'[step350] missing authoritative workflow contract: {needle}')
    if re.search(r'gradlew\s+.*assembleDebug', text):
        raise SystemExit('[step350] workflow must use direct Gradle; wrapper build path detected')
    if 'if: failure()' not in text or 'Upload diagnostics' not in text:
        raise SystemExit('[step350] failure diagnostics contract missing')
    if 'concurrency:' not in text or 'cancel-in-progress: true' not in text:
        raise SystemExit('[step350] CI concurrency contract missing')
    print('[step350] authoritative workflow contracts verified')
    print('[step350] direct Gradle 9.6.0, lint, unit tests, APK build and APK integrity gates are present')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
