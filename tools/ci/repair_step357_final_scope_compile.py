#!/usr/bin/env python3
"""Step 357: final generated Kotlin scope and helper repair.

This runs after all late UI generators and Step349 so generated source reaches
Gradle with concrete Android View APIs, complete server helper declarations, and
real Microsoft/cosmetic UI callbacks.
"""
from pathlib import Path
import re
import subprocess
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")


def normalize_edit_text(text: str) -> str:
    # Raw Android EditText.singleLine is not a Kotlin property in this usage.
    # Compose `singleLine = ...` parameters are left alone by operating on lines
    # that contain an Android EditText declaration or a direct EditText property.
    text = re.sub(r"(android\.widget\.EditText\(this\)\.apply\s*\{[^\n{}]*?)\bsingleLine\s*=\s*(true|false)",
                  lambda m: m.group(1) + "setSingleLine(" + m.group(2) + ")", text)
    text = re.sub(r"(?m)^(\s*)singleLine\s*=\s*(true|false)\s*$",
                  lambda m: m.group(1) + "setSingleLine(" + m.group(2) + ")", text)
    return text


def repair_server_helpers(text: str) -> str:
    # Repair the exact malformed generated pair where serverPrefs lost its
    # expression and the next function was emitted on the following line.
    malformed = re.compile(
        r"(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n"
        r"\s*private fun getSavedServers\(\): List<Pair<String, Int>>\s*\{"
    )
    replacement = (
        "    private fun serverPrefs(): android.content.SharedPreferences =\n"
        "        getSharedPreferences(\"droid_launcher_servers\", MODE_PRIVATE)\n\n"
        "    private fun getSavedServers(): List<Pair<String, Int>> {"
    )
    text, changed = malformed.subn(replacement, text, count=1)

    # A variant may omit the explicit generic return type on getSavedServers.
    malformed_short = re.compile(
        r"(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n"
        r"\s*private fun getSavedServers\(\)\s*\{"
    )
    replacement_short = (
        "    private fun serverPrefs(): android.content.SharedPreferences =\n"
        "        getSharedPreferences(\"droid_launcher_servers\", MODE_PRIVATE)\n\n"
        "    private fun getSavedServers(): List<Pair<String, Int>> {"
    )
    text, changed2 = malformed_short.subn(replacement_short, text, count=1)

    # Never leave an unindented top-level server helper in generated Kotlin.
    names = (
        "getSavedServers", "getServerName", "getServerStatus", "selectServer",
        "deleteServer", "showServerDialog", "refreshServerStatus"
    )
    for name in names:
        text = re.sub(r"(?m)^private fun " + re.escape(name) + r"\b", "    private fun " + name, text)
    return text


def apply_real_microsoft_ui(root: Path) -> str:
    repo_root = Path.cwd().resolve()
    ui = root / UI_REL
    step337 = repo_root / "tools/ci/apply_step337_microsoft_signin_reference_gui.py"
    step352 = repo_root / "tools/ci/apply_step352_real_cosmetic_picker_callback.py"
    if not step337.is_file():
        raise SystemExit("[step357] Step337 Microsoft UI repair is missing")
    if not step352.is_file():
        raise SystemExit("[step357] Step352 cosmetic picker repair is missing")
    subprocess.run([sys.executable, str(step337), str(root)], cwd=repo_root, check=True)
    subprocess.run([sys.executable, str(step352), str(root)], cwd=repo_root, check=True)
    return ui.read_text(encoding="utf-8")


def assert_clean(text: str) -> None:
    required = (
        "private fun serverPrefs(): android.content.SharedPreferences =\n"
        "        getSharedPreferences(\"droid_launcher_servers\", MODE_PRIVATE)",
        "private fun getSavedServers(): List<Pair<String, Int>> {",
        "private fun showMicrosoftSignInPage()",
        "override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?)",
        "setSingleLine(true)",
        "STEP352_REAL_COSMETIC_PICKER_CALLBACK",
    )
    for marker in required:
        if marker not in text:
            raise SystemExit(f"[step357] required final-source marker missing: {marker}")
    if "singleLine =" in text:
        raise SystemExit("[step357] raw singleLine assignment remains in generated activity")
    if text.count("private fun serverPrefs():") != 1:
        raise SystemExit("[step357] serverPrefs declaration count is not exactly one")
    if text.count("private fun showMicrosoftSignInPage()") != 1:
        raise SystemExit("[step357] Microsoft page helper count is not exactly one")
    if text.count("override fun onActivityResult(") != 1:
        raise SystemExit("[step357] ActivityResult callback count is not exactly one")
    if "private fun serverPrefs(): android.content.SharedPreferences =\n    private fun getSavedServers" in text:
        raise SystemExit("[step357] truncated serverPrefs declaration remains")
    if "private fun getServerName(index: Int): String =\n    private fun getServerStatus" in text:
        raise SystemExit("[step357] truncated getServerName declaration remains")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / UI_REL
    if not ui.is_file():
        raise SystemExit(f"[step357] generated UI missing: {ui}")
    text = ui.read_text(encoding="utf-8")
    text = normalize_edit_text(text)
    text = repair_server_helpers(text)
    ui.write_text(text, encoding="utf-8")
    text = apply_real_microsoft_ui(root)
    text = normalize_edit_text(text)
    text = repair_server_helpers(text)
    ui.write_text(text, encoding="utf-8")
    assert_clean(ui.read_text(encoding="utf-8"))
    print("[step357] final generated Kotlin scope/API repair passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
