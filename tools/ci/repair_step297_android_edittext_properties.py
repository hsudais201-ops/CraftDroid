#!/usr/bin/env python3
"""Step 297/298/337/338/339: normalize generated Android APIs and apply final UIs."""
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

    patch337 = Path(__file__).with_name("apply_step337_microsoft_signin_reference_gui.py")
    verifier337 = Path(__file__).with_name("verify_step337_microsoft_signin_gui.py")
    if not patch337.is_file() or not verifier337.is_file():
        raise SystemExit("[step337] Microsoft sign-in GUI patch/verifier missing")
    subprocess.run([sys.executable, str(patch337), str(root)], check=True)
    subprocess.run([sys.executable, str(verifier337), str(root)], check=True)

    patch338 = Path(__file__).with_name("apply_step338_offline_profile_gui.py")
    verifier338 = Path(__file__).with_name("verify_step338_offline_profile_gui.py")
    if not patch338.is_file() or not verifier338.is_file():
        raise SystemExit("[step338] offline profile GUI patch/verifier missing")
    subprocess.run([sys.executable, str(patch338), str(root)], check=True)
    subprocess.run([sys.executable, str(verifier338), str(root)], check=True)

    patch339 = Path(__file__).with_name("apply_step339_settings_renderer_reference_gui.py")
    verifier339 = Path(__file__).with_name("verify_step339_settings_renderer_reference_gui.py")
    if not patch339.is_file() or not verifier339.is_file():
        raise SystemExit("[step339] Settings Renderer GUI patch/verifier missing")
    subprocess.run([sys.executable, str(patch339), str(root)], check=True)
    subprocess.run([sys.executable, str(verifier339), str(root)], check=True)

    print(f"[step297] EditText single-line normalization complete; property replacements={token_replacements}; setter replacements={setter_replacements}")
    print("[step337] Microsoft custom sign-in GUI and top-right Home action finalized after UI generation")
    print("[step338] Offline profile reference GUI and Home return action finalized after UI generation")
    print("[step339] Settings · Renderer reference GUI and working option controls finalized after UI generation")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
