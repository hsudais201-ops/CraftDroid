#!/usr/bin/env python3
"""Step 360: make the generated build self-contained for CI.

The launcher does not use Firebase/Google-services APIs in its current runtime
sources. Do not require a credentials/config file merely to compile the APK.
The Google Services Gradle plugin is therefore removed from the generated app
build, while the source archive itself remains untouched.
"""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    path = root / 'app/build.gradle.kts'
    if not path.is_file():
        alt = root / 'app/build.gradle'
        if alt.is_file():
            path = alt
        else:
            raise SystemExit(f'[step360] missing app Gradle file under {root}')

    text = path.read_text(encoding='utf-8')
    original = text
    text = re.sub(
        r'^import\s+com\.google\.gms\.googleservices\.GoogleServicesPlugin\.MissingGoogleServicesStrategy\s*\n',
        '', text, flags=re.M,
    )
    text = re.sub(r'^\s*alias\(libs\.plugins\.google\.services\)\s*\n', '', text, flags=re.M)
    text = re.sub(
        r'^\s*googleServices\s*\{\s*missingGoogleServicesStrategy\s*=\s*MissingGoogleServicesStrategy\.WARN\s*\}\s*\n',
        '', text, flags=re.M,
    )
    if text != original:
        path.write_text(text, encoding='utf-8')
    final = path.read_text(encoding='utf-8')
    forbidden = (
        'com.google.gms.googleservices.GoogleServicesPlugin',
        'libs.plugins.google.services',
        'googleServices {',
    )
    for marker in forbidden:
        if marker in final:
            raise SystemExit(f'[step360] Google Services build marker remains: {marker}')
    print(f'[step360] CI build contract normalized: {path}; changed={int(text != original)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
