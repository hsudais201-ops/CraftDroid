#!/usr/bin/env python3
"""Step 297/298/337/338/339/340/341/342/344/345/346/347/348: normalize generated Android APIs and apply final UIs."""
from pathlib import Path
import re
import subprocess
import sys
TOKEN = re.compile(r"(?<![A-Za-z0-9_])singleLine(?![A-Za-z0-9_])")
def main() -> int:
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=root/"app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step297] missing generated UI: {ui}")
    source=ui.read_text(encoding="utf-8")
    repaired=TOKEN.sub("isSingleLine",source).replace("setSingleLine(true)","isSingleLine = true")
    ui.write_text(repaired,encoding="utf-8")
    if TOKEN.search(repaired) or "setSingleLine(true)" in repaired: raise SystemExit("[step297] unresolved EditText single-line API remains")
    patches=[
      ("337","apply_step337_microsoft_signin_reference_gui.py","verify_step337_microsoft_signin_gui.py"),
      ("338","apply_step338_offline_profile_gui.py","verify_step338_offline_profile_gui.py"),
      ("339","apply_step339_settings_renderer_reference_gui.py","verify_step339_settings_renderer_reference_gui.py"),
      ("340","apply_step340_settings_reference_polish.py","verify_step340_settings_reference_polish.py"),
      ("341","apply_step341_download_manager_reference_gui.py","verify_step341_download_manager_reference_gui.py"),
      ("342","apply_step342_content_install_picker.py","verify_step342_content_install_picker.py"),
      ("344","apply_step344_download_world_and_dependencies.py","verify_step344_download_world_and_dependencies.py"),
      ("345","apply_step345_required_mods_after_download.py","verify_step345_required_mods_after_download.py"),
      ("346","apply_step346_version_instance_reference_screen.py","verify_step346_version_instance_reference_screen.py"),
      ("347","apply_step347_version_instance_pixel_layout.py","verify_step347_version_instance_pixel_layout.py"),
      ("348","apply_step348_version_instance_actions.py","verify_step348_version_instance_actions.py"),
    ]
    for step,patch_name,verifier_name in patches:
        patch=Path(__file__).with_name(patch_name); verifier=Path(__file__).with_name(verifier_name)
        if not patch.is_file() or not verifier.is_file(): raise SystemExit(f"[step{step}] patch/verifier missing")
        subprocess.run([sys.executable,str(patch),str(root)],check=True)
        subprocess.run([sys.executable,str(verifier),str(root)],check=True)
    print("[step297-348] final UI/action repair chain complete")
    return 0
if __name__=="__main__": raise SystemExit(main())
