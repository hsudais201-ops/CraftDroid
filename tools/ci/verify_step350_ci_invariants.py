#!/usr/bin/env python3
"""Step 350: validate the authoritative build workflow and requested feature coverage."""
from pathlib import Path
import re
import subprocess
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
        'repair_step297_android_edittext_properties.py',
        'verify_step337_microsoft_signin_gui.py',
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

    critical = root / 'tools/ci/verify_critical_repository_files.py'
    if not critical.is_file():
        raise SystemExit('[step350] critical-file preservation verifier missing')
    subprocess.run([sys.executable, str(critical), str(root)], cwd=root, check=True)

    coverage = root / 'tools/ci/verify_important_feature_coverage.py'
    generated = root / 'droid-src'
    if not coverage.is_file():
        raise SystemExit('[step350] important feature coverage verifier missing')

    # Step357 is an explicit final generated-source repair stage. The workflow
    # invokes Step349 first; this guard makes the final scope/API repair unavoidable
    # before the invariant audit and before the Gradle compiler runs.
    final_scope = root / 'tools/ci/repair_step357_final_scope_compile.py'
    if not final_scope.is_file():
        raise SystemExit('[step350] Step357 final generated scope repair is missing')
    if generated.is_dir():
        subprocess.run([sys.executable, str(final_scope), str(generated)], cwd=root, check=True)
        subprocess.run([sys.executable, str(coverage), str(generated)], cwd=root, check=True)
    else:
        print('[step350] generated source tree is unavailable; feature coverage will run in the workflow after generation')

    verifier_requirements = {
        'tools/ci/verify_step337_microsoft_signin_gui.py': ('openCosmeticImagePicker(3371)', 'takePersistableUriPermission'),
        'tools/ci/verify_important_feature_coverage.py': ('microsoft_skin_uri', 'microsoft_cape_uri', 'STEP352_REAL_COSMETIC_PICKER_CALLBACK'),
        'tools/ci/repair_step357_final_scope_compile.py': ('repair_server_helpers', 'normalize_edit_text', 'showMicrosoftSignInPage'),
    }
    for rel, markers in verifier_requirements.items():
        path = root / rel
        if not path.is_file():
            raise SystemExit(f'[step350] verifier/repair missing: {rel}')
        verifier_text = path.read_text(encoding='utf-8', errors='replace')
        for marker in markers:
            if marker not in verifier_text:
                raise SystemExit(f'[step350] contract missing from {rel}: {marker}')

    print('[step350] authoritative workflow contracts verified')
    print('[step350] direct Gradle 9.6.0, lint, unit tests, APK build and APK integrity gates are present')
    print('[step350] Microsoft/skin-cape picker and requested launcher subsystem coverage verifiers are chained into CI')
    print('[step350] critical-file preservation audit is chained into CI')
    print('[step350] Step357 final generated scope/API repair is chained before Gradle')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
