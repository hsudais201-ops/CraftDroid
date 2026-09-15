#!/usr/bin/env python3
"""Step 239/291/292: verify generated Kotlin without destroying later UI stages."""
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


def patch_base_navigation(ui: str) -> str:
    """Only normalize the pre-bootstrap UI; never rerun Step 286 over Step 287."""
    if '"Features" -> featuresPage()' not in ui:
        anchor = '            "Controls" -> controlsPage()'
        if anchor in ui:
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
        else:
            anchor = '            "Renderer" -> rendererPage()'
            if anchor not in ui:
                raise SystemExit('[step291] showPage navigation anchor missing')
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)

    # The supplied Home/Account UI does not use the historical glyph-list form.
    # Add the Features item only when a real navigation list exists.
    if '"✦" to "Features"' not in ui:
        match = re.search(r'(?m)^(\s*)(.*"⌕"\s+to\s+"Search by ID",)(.*)$', ui)
        if match:
            replacement = f'{match.group(1)}{match.group(2)} "✦" to "Features",{match.group(3)}'
            ui = ui[:match.start()] + replacement + ui[match.end():]

    if 'contentDescription = "Account mockup home"' not in ui and 'private fun accountPage()' in ui:
        marker = '    private fun accountPage() {\n'
        if marker in ui:
            header = '''    private fun accountPage() {\n        val accountHeader = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }\n        accountHeader.addView(label("Profiles", 18f, true), LinearLayout.LayoutParams(0, dp(58), 1f))\n        val accountHome = button("⌂  Home")\n        accountHome.contentDescription = "Account mockup home"\n        accountHome.setOnClickListener { showPage("Game") }\n        accountHeader.addView(accountHome, LinearLayout.LayoutParams(dp(150), dp(58)))\n        pageArea.addView(accountHeader)\n'''
            ui = ui.replace(marker, header, 1)

    return ui


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    ui_path = find_one(src, "DroidLauncherUiActivity.kt")
    ui = ui_path.read_text(encoding="utf-8")

    # Step 287 is already authoritative at this point. Re-running Step 286 here
    # used to delete the first-run gate and caused duplicate onCreate declarations.
    if "private fun showBootstrapGate()" not in ui:
        final_ui_script = root.parent / "tools/ci/apply_step286_home_account_gui.py"
        if not final_ui_script.is_file():
            raise SystemExit(f"[step291] final UI script not found: {final_ui_script}")
        namespace = runpy.run_path(str(final_ui_script), run_name="step286_helper")
        result = namespace["main"]()
        if result not in (None, 0):
            raise SystemExit(f"[step291] final UI helper returned {result}")
        ui = ui_path.read_text(encoding="utf-8")
        ui = patch_base_navigation(ui)
        ui = ui.replace('setTextColor(text)', 'setTextColor(primaryText)')
        ui_path.write_text(ui, encoding="utf-8")
        ui = ui_path.read_text(encoding="utf-8")
    else:
        # Bootstrap source must be treated as immutable UI at this verification stage.
        if 'setTextColor(this@DroidLauncherUiActivity.text)' in ui or 'setTextColor(text)' in ui:
            raise SystemExit('[step292] invalid generated text color reference remains')

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

    required = (
        'private fun homePage()',
        'private fun accountPage()',
        '"Accounts" -> accountPage()',
        '"Game" -> homePage()',
        '"Features" -> featuresPage()',
        'setOnClickListener { showPage("Accounts") }',
        'setOnClickListener { showPage("Game") }',
        'ScrollView(this)',
        'SCREEN_ORIENTATION_LANDSCAPE',
    )
    for needle in required:
        if needle not in ui:
            raise SystemExit(f'[step291] final GUI contract missing: {needle}')

    server_helpers = (
        'private fun showServerDialog(',
        'private fun getSavedServers()',
        'private fun refreshServerStatus(',
        'private fun deleteServer(',
        'private fun selectServer(',
    )
    if 'private fun showBootstrapGate()' in ui:
        for needle in server_helpers:
            if needle not in ui:
                raise SystemExit(f'[step292] server contract missing: {needle}')

    if 'private fun showBootstrapGate()' in ui:
        print('[step287] bootstrap gate preserved during generated-source verification')
    print('[step239] generated UI helper declarations are unique')
    print('[step239] MinecraftLaunchManager Java resolver is Int -> Int')
    print('[step239] no stale String-based Java launch resolver remains')
    print('[step291] Home + Account/Profile mockups finalized with preserved Feature Center navigation')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
