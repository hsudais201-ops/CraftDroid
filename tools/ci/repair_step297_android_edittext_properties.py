#!/usr/bin/env python3
"""Step 297/298/337/338/339/340/341/342/344/345/346: normalize generated Android APIs and apply final UIs."""
from pathlib import Path
import re
import subprocess
import sys

TOKEN = re.compile(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])")

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step297] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    token_replacements = len(TOKEN.findall(source))
    repaired = TOKEN.sub("isSingleLine", source)
    setter_replacements = repaired.count("setSingleLine(true)")
    repaired = repaired.replace("setSingleLine(true)", "isSingleLine = true")
    ui.write_text(repaired, encoding="utf-8")
    if TOKEN.search(repaired) or "setSingleLine(true)" in repaired:
        raise SystemExit("[step297] unresolved EditText single-line API remains")

    patches = [
        ("337", "apply_step337_microsoft_signin_reference_gui.py", "verify_step337_microsoft_signin_gui.py", "Microsoft sign-in GUI patch/verifier missing"),
        ("338", "apply_step338_offline_profile_gui.py", "verify_step338_offline_profile_gui.py", "offline profile GUI patch/verifier missing"),
        ("339", "apply_step339_settings_renderer_reference_gui.py", "verify_step339_settings_renderer_reference_gui.py", "Settings Renderer GUI patch/verifier missing"),
        ("340", "apply_step340_settings_reference_polish.py", "verify_step340_settings_reference_polish.py", "Settings reference polish patch/verifier missing"),
        ("341", "apply_step341_download_manager_reference_gui.py", "verify_step341_download_manager_reference_gui.py", "3.jpeg download/install/version GUI patch/verifier missing"),
        ("342", "apply_step342_content_install_picker.py", "verify_step342_content_install_picker.py", "real content install picker patch/verifier missing"),
        ("344", "apply_step344_download_world_and_dependencies.py", "verify_step344_download_world_and_dependencies.py", "one-click download/required/world patch/verifier missing"),
        ("345", "apply_step345_required_mods_after_download.py", "verify_step345_required_mods_after_download.py", "required-mod post-download patch/verifier missing"),
        ("346", "apply_step346_version_instance_reference_screen.py", "verify_step346_version_instance_reference_screen.py", "Version / Instances reference screen patch/verifier missing"),
    ]
    for step, patch_name, verifier_name, error_text in patches:
        patch = Path(__file__).with_name(patch_name)
        verifier = Path(__file__).with_name(verifier_name)
        if not patch.is_file() or not verifier.is_file():
            raise SystemExit(f"[step{step}] {error_text}")
        subprocess.run([sys.executable, str(patch), str(root)], check=True)
        subprocess.run([sys.executable, str(verifier), str(root)], check=True)

    print(f"[step297] EditText single-line normalization complete; property replacements={token_replacements}; setter replacements={setter_replacements}")
    print("[step337] Microsoft custom sign-in GUI finalized")
    print("[step338] Offline profile reference GUI finalized")
    print("[step339] Settings Renderer reference GUI finalized")
    print("[step340] Settings reference shell polished")
    print("[step341] 3.jpeg Download/install/version manager GUI finalized")
    print("[step342] Modpack/Mod/Shader/Resource Pack local import support finalized")
    print("[step344] One-click Modrinth downloads, required dependency display, and Worlds manager finalized")
    print("[step345] Required-mod dialog now appears after modpack download")
    print("[step346] Version / Instances reference screen finalized; + opens Game download/version manager")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
