#!/usr/bin/env python3
"""Final generated UI repair chain through Step352."""
from pathlib import Path
import re
import subprocess
import sys

TOKEN = re.compile(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])")
PAIRS = [
    ('337', 'apply_step337_microsoft_signin_reference_gui.py', 'verify_step337_microsoft_signin_gui.py'),
    ('338', 'apply_step338_offline_profile_gui.py', 'verify_step338_offline_profile_gui.py'),
    ('339', 'apply_step339_settings_renderer_reference_gui.py', 'verify_step339_settings_renderer_reference_gui.py'),
    ('340', 'apply_step340_settings_reference_polish.py', 'verify_step340_settings_reference_polish.py'),
    ('341', 'apply_step341_download_manager_reference_gui.py', 'verify_step341_download_manager_reference_gui.py'),
    ('342', 'apply_step342_content_install_picker.py', 'verify_step342_content_install_picker.py'),
    ('344', 'apply_step344_download_world_and_dependencies.py', 'verify_step344_download_world_and_dependencies.py'),
    ('345', 'apply_step345_required_mods_after_download.py', 'verify_step345_required_mods_after_download.py'),
    ('346', 'apply_step346_version_instance_reference_screen.py', 'verify_step346_version_instance_reference_screen.py'),
    ('347', 'apply_step347_version_instance_pixel_layout.py', 'verify_step347_version_instance_pixel_layout.py'),
    ('348', 'apply_step348_version_instance_actions.py', 'verify_step348_version_instance_actions.py'),
]


def run_pair(root: Path, n: str, patch: str, verify: str) -> None:
    pp = Path(__file__).with_name(patch)
    vv = Path(__file__).with_name(verify)
    if not pp.is_file() or not vv.is_file():
        raise SystemExit(f'step{n} patch/verifier missing: patch={pp.name} verifier={vv.name}')
    subprocess.run([sys.executable, str(pp), str(root)], check=True)
    subprocess.run([sys.executable, str(vv), str(root)], check=True)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file():
        raise SystemExit('generated UI missing')

    s = ui.read_text(encoding='utf-8')
    s = TOKEN.sub('isSingleLine', s).replace('setSingleLine(true)', 'isSingleLine = true')
    ui.write_text(s, encoding='utf-8')

    for n, patch, verify in PAIRS:
        run_pair(root, n, patch, verify)

    # Step 352 consumes the existing Step 342 Activity Result callback and makes
    # the Microsoft-page skin/cape selectors persist real document URIs.
    cosmetic_patch = Path(__file__).with_name('apply_step352_real_cosmetic_picker_callback.py')
    if not cosmetic_patch.is_file():
        raise SystemExit('step352 real cosmetic picker patch is missing')
    subprocess.run([sys.executable, str(cosmetic_patch), str(root)], check=True)
    cosmetic_marker = '// STEP352_REAL_COSMETIC_PICKER_CALLBACK'
    final_text = ui.read_text(encoding='utf-8')
    if cosmetic_marker not in final_text:
        raise SystemExit('step352 cosmetic callback marker missing after patch')

    # The later Version / Instances steps replace a large method block in the same
    # generated Kotlin file. Re-assert the Settings/Renderer reference contract at
    # the end so downstream whole-method rewrites cannot erase Step340's styling.
    run_pair(root, '340-final', 'apply_step340_settings_reference_polish.py', 'verify_step340_settings_reference_polish.py')

    # Final compile-boundary repair runs after every late UI rewrite in this chain.
    final_repair = Path(__file__).with_name('repair_step349_final_generated_compile.py')
    if not final_repair.is_file():
        raise SystemExit('step349 final generated compile repair is missing')
    subprocess.run([sys.executable, str(final_repair), str(root)], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
