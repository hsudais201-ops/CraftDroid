#!/usr/bin/env python3
"""Step 297/298/337/338/339/340/341/342: normalize generated Android APIs and apply final UIs."""
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
    ]
    for step, patch_name, verifier_name, error_text in patches:
        patch = Path(__file__).with_name(patch_name)
        verifier = Path(__file__).with_name(verifier_name)
        if not patch.is_file() or not verifier.is_file():
            raise SystemExit(f"[step{step}] {error_text}")
        subprocess.run([sys.executable, str(patch), str(root)], check=True)
        subprocess.run([sys.executable, str(verifier), str(root)], check=True)

    print(f"[step297] EditText single-line normalization complete; property replacements={token_replacements}; setter replacements={setter_replacements}")
    print("[step337] Microsoft custom sign-in GUI and top-right Home action finalized after UI generation")
    print("[step338] Offline profile reference GUI and Home return action finalized after UI generation")
    print("[step339] Settings · Renderer reference GUI and working option controls finalized after UI generation")
    print("[step340] Settings reference shell polished to match 2.jpeg")
    print("[step341] 3.jpeg Download/install/version manager GUI finalized after UI generation")
    print("[step342] Modpack/Mod/Shader/Resource Pack Install buttons now import real local files")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
