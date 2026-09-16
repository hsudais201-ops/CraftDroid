#!/usr/bin/env python3
"""Step 333: final generated-source authority before quality/Gradle.

Repairs semantic duplicate helpers and known Android generated-source regressions
introduced by late UI generators. Idempotent by construction.

The launcher pipeline has two valid phases: an early generated-UI phase (before
Step 293 installs the server contract) and the final phase (after Step 293). In
the final phase, if a late generator has accidentally removed the server contract,
Step 333 restores it before continuing normalization and verification.
"""
from pathlib import Path
import subprocess
import sys


def function_end(source: str, start: int) -> int:
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step333] missing body for function at {start}")
    depth = 0
    in_string = False
    in_triple = False
    in_char = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    i = brace
    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""
        nxt2 = source[i + 2] if i + 2 < len(source) else ""
        if in_line_comment:
            if ch == "\n": in_line_comment = False
            i += 1; continue
        if in_block_comment:
            if ch == "*" and nxt == "/": in_block_comment = False; i += 2; continue
            i += 1; continue
        if in_triple:
            if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = False; i += 3; continue
            i += 1; continue
        if in_string:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
            i += 1; continue
        if in_char:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == "'": in_char = False
            i += 1; continue
        if ch == "/" and nxt == "/": in_line_comment = True; i += 2; continue
        if ch == "/" and nxt == "*": in_block_comment = True; i += 2; continue
        if ch == '"' and nxt == '"' and nxt2 == '"': in_triple = True; i += 3; continue
        if ch == '"': in_string = True; i += 1; continue
        if ch == "'": in_char = True; i += 1; continue
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                j = i + 1
                while j < len(source) and source[j] in "\r\n": j += 1
                return j
        i += 1
    raise SystemExit("[step333] unterminated function body")


def dedupe_signature(source: str, signature: str) -> tuple[str, int]:
    starts = []
    offset = 0
    while True:
        pos = source.find(signature, offset)
        if pos < 0: break
        starts.append(pos); offset = pos + 1
    if len(starts) <= 1:
        return source, 0
    removed = 0
    for pos in reversed(starts[1:]):
        end = function_end(source, pos)
        source = source[:pos] + source[end:]
        removed += 1
    return source, removed


SIGNATURES = (
    "private fun serverPrefs(): android.content.SharedPreferences",
    "private fun getSavedServers(): List<Pair<String, Int>>",
    "private fun getServerName(index: Int): String",
    "private fun getServerStatus(host: String, port: Int): String",
    "private fun selectServer(host: String, port: Int)",
    "private fun deleteServer(index: Int)",
    "private fun showServerDialog(index: Int)",
    "private fun refreshServerStatus(host: String, port: Int)",
    "private fun selectedMinecraftVersion(): String",
    "private fun selectedMinecraftProfile(): String",
    "private fun saveMinecraftVersion(version: String)",
    "private fun saveMinecraftProfile(profile: String)",
    "private fun launchSelectedMinecraft()",
)


def normalize(source: str) -> str:
    source = source.replace("this@DroidLauncherUiActivity.text", "primaryText")
    source = source.replace("setTextColor(text)", "setTextColor(primaryText)")
    source = source.replace("singleLine = true", "isSingleLine = true")
    source = source.replace("setSingleLine(true)", "isSingleLine = true")
    for sig in SIGNATURES:
        source, _ = dedupe_signature(source, sig)
    return source


def restore_final_server_contract(root: Path, path: Path, source: str) -> str:
    required_server = SIGNATURES[:8]
    present_server = [sig for sig in required_server if sig in source]
    if present_server or "private fun showBootstrapGate()" not in source:
        return source

    script = Path(__file__).with_name("repair_step293_server_contracts_after_final_ui.py")
    if not script.is_file():
        raise SystemExit("[step333] final-phase server contract is missing and Step 293 script is unavailable")
    print("[step333] final-phase server contract missing; restoring through Step 293")
    subprocess.run([sys.executable, str(script), str(root)], check=True)
    restored = path.read_text(encoding="utf-8")
    return normalize(restored)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not path.is_file():
        raise SystemExit(f"[step333] missing UI source: {path}")

    source = path.read_text(encoding="utf-8")
    source = normalize(source)
    source = restore_final_server_contract(root, path, source)

    # A late generator can reintroduce duplicates while Step 293 is restoring the
    # contract, so normalize/dedupe one more time after the restoration boundary.
    source = normalize(source)

    required_server = SIGNATURES[:8]
    present_server = [sig for sig in required_server if sig in source]
    if present_server and len(present_server) != len(required_server):
        missing = [sig for sig in required_server if sig not in source]
        raise SystemExit(
            "[step333] partial server contract detected; missing: " + ", ".join(missing)
        )
    if not present_server:
        print("[step333] server contract not present yet; deferring to Step 293 final UI repair")

    duplicates = [sig for sig in SIGNATURES if source.count(sig) != 1 and (present_server or sig not in required_server)]
    if present_server and duplicates:
        raise SystemExit("[step333] duplicate/missing critical helper: " + ", ".join(duplicates))

    forbidden = (
        "this@DroidLauncherUiActivity.text",
        "setTextColor(text)",
        "singleLine = true",
        "setSingleLine(true)",
    )
    stale = [token for token in forbidden if token in source]
    if stale:
        raise SystemExit("[step333] stale generated Android token remains: " + ", ".join(stale))

    path.write_text(source, encoding="utf-8")

    # Step 334 is deliberately the final Home-server presentation pass so that
    # later contract generators cannot remove the Delete button beside Edit.
    step334 = Path(__file__).with_name("apply_step334_server_toolbar_delete.py")
    if step334.is_file():
        subprocess.run([sys.executable, str(step334), str(root)], check=True)
    else:
        raise SystemExit("[step333] required Step 334 server toolbar patch is missing")

    # Step 336 supplies the installed-version inventory consumed by Step 335.
    step336 = Path(__file__).with_name("apply_step336_version_manager_inventory.py")
    if step336.is_file():
        subprocess.run([sys.executable, str(step336), str(root)], check=True)
    else:
        raise SystemExit("[step333] required Step 336 version-inventory patch is missing")

    # Step 335 is the final Home presentation pass: installed version/instance
    # selection sits immediately above Launch and active downloads stay visible.
    step335 = Path(__file__).with_name("apply_step335_home_version_instance_downloads.py")
    if step335.is_file():
        subprocess.run([sys.executable, str(step335), str(root)], check=True)
    else:
        raise SystemExit("[step333] required Step 335 Home download/selector patch is missing")

    print("[step333] final generated source authority applied")
    if present_server:
        print("[step333] server helper ownership normalized to exactly one implementation")
    else:
        print("[step333] early generated-source phase passed without requiring deferred server helpers")
    print("[step333] Android text-color and EditText APIs canonicalized")
    print("[step335] Home version/instance selector + live download progress applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
