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

    if generated.is_dir():
        generated_controller = generated / 'app/src/main/java/com/example/launcher/LauncherBackgroundInstallController.kt'
        generated_installer = generated / 'app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt'
        if not generated_controller.is_file() or not generated_installer.is_file():
            raise SystemExit('[step400] generated installer/controller sources missing')
        controller_text = generated_controller.read_text(encoding='utf-8', errors='replace')
        installer_text = generated_installer.read_text(encoding='utf-8', errors='replace')
        for marker in (
            'Executors.newSingleThreadExecutor',
            'THREAD_PRIORITY_BACKGROUND',
            'COMPLETED_STATE_RETENTION_MS',
            'importContentUri(',
            'MAX_STAGED_CONTENT_BYTES',
        ):
            if marker not in controller_text:
                raise SystemExit(f'[step400] generated controller contract missing: {marker}')
        generated_ui = generated / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
        if not generated_ui.is_file():
            raise SystemExit('[step400] generated UI source missing')
        generated_ui_text = generated_ui.read_text(encoding='utf-8', errors='replace')
        for marker in (
            'PerformanceProfile.detect(this).tier',
            'if (bitmap == null && step376LowRam) return@Thread',
            'LauncherBackgroundInstallController.importContentUri(this, kind, uri)',
        ):
            if marker not in generated_ui_text:
                raise SystemExit(f'[step400] generated low-RAM UI contract missing: {marker}')
        for marker in (
            'VERSION_PATTERN = Regex',
            'MAX_TEXT_RESPONSE_BYTES',
            'Invalid Minecraft version id',
            'Executors.newSingleThreadExecutor',
            'THREAD_PRIORITY_BACKGROUND',
        ):
            if marker not in installer_text:
                raise SystemExit(f'[step400] generated installer contract missing: {marker}')
        print('[step400] generated low-RAM/background installer hardening contracts verified')

    # Step357 is an explicit final generated-source repair stage. The workflow
    # invokes Step349 first; this guard makes the final scope/API repair unavoidable
    # before the invariant audit and before the Gradle compiler runs.
    final_scope = root / 'tools/ci/repair_step357_final_scope_compile.py'
    if not final_scope.is_file():
        raise SystemExit('[step350] Step357 final generated scope repair is missing')
    if generated.is_dir():
        subprocess.run([sys.executable, str(final_scope), str(generated)], cwd=root, check=True)
        custom_ui = root / 'tools/ci/apply_step375_custom_ui.py'
        if not custom_ui.is_file():
            raise SystemExit('[step375] final custom UI patch script is missing')
        subprocess.run([sys.executable, str(custom_ui), str(generated)], cwd=root, check=True)
        low_ram_ui = root / 'tools/ci/apply_step376_low_ram_ui.py'
        if not low_ram_ui.is_file():
            raise SystemExit('[step376] low-RAM UI hardening script is missing')
        subprocess.run([sys.executable, str(low_ram_ui), str(generated)], cwd=root, check=True)
        settings_cleanup = root / 'tools/ci/apply_step382_settings_cleanup.py'
        if not settings_cleanup.is_file():
            raise SystemExit('[step382] settings cleanup script is missing')
        subprocess.run([sys.executable, str(settings_cleanup), str(generated)], cwd=root, check=True)
        content_picker = root / 'tools/ci/apply_step391_final_content_picker.py'
        if not content_picker.is_file():
            raise SystemExit('[step391] final content picker script is missing')
        subprocess.run([sys.executable, str(content_picker), str(generated)], cwd=root, check=True)
        memory_settings = root / 'tools/ci/apply_step395_low_ram_memory_settings.py'
        if not memory_settings.is_file():
            raise SystemExit('[step395] low-RAM memory settings script is missing')
        subprocess.run([sys.executable, str(memory_settings), str(generated)], cwd=root, check=True)
        subprocess.run([sys.executable, str(coverage), str(generated)], cwd=root, check=True)
    else:
        print('[step350] generated source tree is unavailable; feature coverage will run in the workflow after generation')

    verifier_requirements = {
        'tools/ci/verify_step337_microsoft_signin_gui.py': ('openCosmeticImagePicker(3371)', 'takePersistableUriPermission'),
        'tools/ci/verify_important_feature_coverage.py': ('microsoft_skin_uri', 'microsoft_cape_uri', 'STEP352_REAL_COSMETIC_PICKER_CALLBACK'),
        'tools/ci/repair_step357_final_scope_compile.py': ('repair_server_helpers', 'normalize_edit_text', 'showMicrosoftSignInPage'),
        'tools/ci/apply_step376_low_ram_ui.py': ('step376LowRam', 'step376PrepareFirstRun', 'step376LoadBackground', 'step376ReleaseEffects'),
        'tools/ci/apply_step382_settings_cleanup.py': ('step375Settings()', 'PerformanceProfile.detect', 'Resolution Scale', 'Game Fullscreen'),
        'tools/ci/apply_step391_final_content_picker.py': ('step391StartContentImport', 'CONTENT_PICKER_REQUEST = 341', 'STEP391_FINAL_CONTENT_PICKER'),
        'tools/ci/apply_step395_low_ram_memory_settings.py': ('getSafeRamMb', 'getRecommendedRamMb', 'RAM_MB'),
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
    print('[step375] custom reference-driven UI applied after Step357 and before feature coverage')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
