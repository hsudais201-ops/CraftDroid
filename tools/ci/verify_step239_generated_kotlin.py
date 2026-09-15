#!/usr/bin/env python3
"""Step 239/287: verify generated Kotlin and apply the final supplied UI shell."""
from pathlib import Path
import re
import runpy
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step239] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def count_decl(source: str, signature: str) -> int:
    return len(re.findall(re.escape(signature), source))


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()

    # runpy must use __main__ so the final UI script's main() actually executes.
    final_ui_script = root.parent / "tools/ci/apply_step286_home_account_gui.py"
    if not final_ui_script.is_file():
        raise SystemExit(f"[step287] final UI script not found: {final_ui_script}")
    runpy.run_path(str(final_ui_script), run_name="__main__")

    src = root / "app/src/main/java"
    ui = find_one(src, "DroidLauncherUiActivity.kt").read_text(encoding="utf-8")
    manager = find_one(src, "MinecraftLaunchManager.kt").read_text(encoding="utf-8")

    for signature in (
        'private fun launchSelectedMinecraft()',
        'private fun installMinecraftVersion(version: String)',
        'private fun selectedMinecraftVersion(): String',
        'private fun selectedMinecraftProfile(): String',
    ):
        count = count_decl(ui, signature)
        if count != 1:
            raise SystemExit(f"[step239] {signature} must have exactly one declaration, found {count}")

    for needle in (
        'private fun resolveLaunchJavaRuntime(requestedJava: Int): Int',
        'javaManager.ensureRuntime(resolveLaunchJavaRuntime(requiredJava))',
    ):
        if needle not in manager:
            raise SystemExit(f"[step239] missing manager type-safety contract: {needle}")

    if 'resolveLaunchJavaRuntime(requestedJava: String): String' in manager:
        raise SystemExit('[step239] stale String-based launch Java resolver remains')
    if 'private fun installMinecraftVersion(version: String) {' not in ui:
        raise SystemExit('[step239] installer declaration missing')

    for needle in (
        'private fun homePage()',
        'private fun accountPage()',
        '"Accounts" -> accountPage()',
        '"Game" -> homePage()',
    ):
        if needle not in ui:
            raise SystemExit(f'[step287] final GUI contract missing: {needle}')

    print('[step239] generated UI helper declarations are unique')
    print('[step239] MinecraftLaunchManager Java resolver is Int -> Int')
    print('[step239] no stale String-based Java launch resolver remains')
    print('[step287] supplied Home + Account/Profile GUI applied and verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
