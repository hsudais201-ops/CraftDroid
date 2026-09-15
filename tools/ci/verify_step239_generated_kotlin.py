#!/usr/bin/env python3
"""Step 239/290: verify generated Kotlin and finalize the supplied Home/Account UI."""
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


def patch_final_navigation(ui: str) -> str:
    if '"Features" -> featuresPage()' not in ui:
        anchor = '            "Controls" -> controlsPage()'
        if anchor in ui:
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
        else:
            anchor = '            "Renderer" -> rendererPage()'
            if anchor not in ui:
                raise SystemExit('[step290] showPage navigation anchor missing')
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)

    if 'contentDescription = "Account mockup home"' not in ui:
        marker = '    private fun accountPage() {\n'
        if marker not in ui:
            raise SystemExit('[step290] accountPage anchor missing')
        header = '''    private fun accountPage() {\n        val accountHeader = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }\n        accountHeader.addView(label("Profiles", 18f, true), LinearLayout.LayoutParams(0, dp(58), 1f))\n        val accountHome = button("⌂  Home")\n        accountHome.contentDescription = "Account mockup home"\n        accountHome.setOnClickListener { showPage("Game") }\n        accountHeader.addView(accountHome, LinearLayout.LayoutParams(dp(150), dp(58)))\n        pageArea.addView(accountHeader)\n'''
        ui = ui.replace(marker, header, 1)

    # TextView.apply changes the receiver for `text`; qualify the Activity color
    # so the generated source cannot accidentally pass CharSequence to setTextColor.
    ui = ui.replace('setTextColor(text)', 'setTextColor(this@DroidLauncherUiActivity.text)')
    return ui


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    final_ui_script = root.parent / "tools/ci/apply_step286_home_account_gui.py"
    if not final_ui_script.is_file():
        raise SystemExit(f"[step290] final UI script not found: {final_ui_script}")

    namespace = runpy.run_path(str(final_ui_script), run_name="step286_helper")
    result = namespace["main"]()
    if result not in (None, 0):
        raise SystemExit(f"[step290] final UI helper returned {result}")

    src = root / "app/src/main/java"
    ui_path = find_one(src, "DroidLauncherUiActivity.kt")
    ui = patch_final_navigation(ui_path.read_text(encoding="utf-8"))
    ui_path.write_text(ui, encoding="utf-8")
    ui = ui_path.read_text(encoding="utf-8")
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
        '"Features" -> featuresPage()',
        'contentDescription = "Account mockup home"',
        'setOnClickListener { showPage("Accounts") }',
        'setOnClickListener { showPage("Game") }',
        'ScrollView(this)',
        'SCREEN_ORIENTATION_LANDSCAPE',
    ):
        if needle not in ui:
            raise SystemExit(f'[step290] final GUI contract missing: {needle}')

    if 'setTextColor(text)' in ui:
        raise SystemExit('[step290] unqualified TextView text color remains')

    print('[step239] generated UI helper declarations are unique')
    print('[step239] MinecraftLaunchManager Java resolver is Int -> Int')
    print('[step239] no stale String-based Java launch resolver remains')
    print('[step290] Home + Account/Profile mockups finalized, scroll-safe and navigation-safe')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
