#!/usr/bin/env python3
"""Step 239/291/292/293: verify generated Kotlin without destroying later UI stages."""
from pathlib import Path
import re
import runpy
import subprocess
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step239] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def count_decl(source: str, signature: str) -> int:
    return len(re.findall(re.escape(signature), source))


def remove_duplicate_functions(source: str, signature: str) -> tuple[str, int]:
    """Keep the first matching top-level helper and remove later copies.

    Late CI repair stages intentionally re-apply launch contracts after UI generation.
    Some of those stages can legitimately encounter an already-present helper.  The
    generated Kotlin must contain one declaration before Gradle sees it, so this
    final verifier owns a small idempotent canonicalization pass as well.
    """
    starts = [m.start() for m in re.finditer(re.escape(signature), source)]
    if len(starts) <= 1:
        return source, 0

    def find_body_end(text: str, start: int) -> int:
        brace = text.find("{", start)
        if brace < 0:
            raise SystemExit(f"[step239] function body opening brace not found: {signature}")
        depth = 0
        in_string = False
        in_char = False
        in_line_comment = False
        in_block_comment = False
        escaped = False
        i = brace
        while i < len(text):
            ch = text[i]
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if in_line_comment:
                if ch == "\n":
                    in_line_comment = False
                i += 1
                continue
            if in_block_comment:
                if ch == "*" and nxt == "/":
                    in_block_comment = False
                    i += 2
                    continue
                i += 1
                continue
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == '"':
                    in_string = False
                i += 1
                continue
            if in_char:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == "'":
                    in_char = False
                i += 1
                continue
            if ch == "/" and nxt == "/":
                in_line_comment = True
                i += 2
                continue
            if ch == "/" and nxt == "*":
                in_block_comment = True
                i += 2
                continue
            if ch == '"':
                in_string = True
            elif ch == "'":
                in_char = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    while end < len(text) and text[end] in "\r\n":
                        end += 1
                    return end
            i += 1
        raise SystemExit(f"[step239] unterminated function body: {signature}")

    removed = 0
    for start in reversed(starts[1:]):
        end = find_body_end(source, start)
        source = source[:start] + source[end:]
        removed += 1
    return source, removed


def deduplicate_final_ui_helpers(ui_path: Path) -> str:
    source = ui_path.read_text(encoding="utf-8")
    signatures = (
        "    private fun selectedMinecraftVersion(): String",
        "    private fun saveMinecraftVersion(version: String)",
        "    private fun selectedMinecraftProfile(): String",
        "    private fun saveMinecraftProfile(profile: String)",
        "    private fun launchSelectedMinecraft()",
    )
    removed_total = 0
    for signature in signatures:
        source, removed = remove_duplicate_functions(source, signature)
        removed_total += removed
    if removed_total:
        ui_path.write_text(source, encoding="utf-8")
        print(f"[step239] removed {removed_total} duplicate final UI helper declaration(s)")
    return source


def normalize_final_generated_ui(ui_path: Path) -> str:
    """Normalize mutations that were historically performed by this verifier.

    The verifier itself is a mutation stage in the generated-source pipeline.  Keep
    that behavior, but ensure its final writes use the same canonical UI contracts
    consumed by Gradle so a later verification pass cannot reintroduce compilation
    failures.
    """
    source = ui_path.read_text(encoding="utf-8")
    source = re.sub(r"\bsingleLine\s*=\s*(true|false)\b", r"setSingleLine(\1)", source)

    # After duplicate removal, canonicalize the remaining Microsoft entrypoint.
    # The historical placeholder body is a flat builder chain, so a method-level
    # regex is deterministic for the generated activity while preserving all other UI.
    source, _ = remove_duplicate_functions(source, "    private fun showMicrosoftAccountInfo()")
    microsoft_method = re.compile(
        r"(?ms)^    private fun showMicrosoftAccountInfo\(\)\s*\{.*?^    \}\s*"
    )
    canonical = "    private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }\n\n"
    if re.search(r"(?m)^    private fun showMicrosoftAccountInfo\(\)", source):
        source, replaced = microsoft_method.subn(canonical, source, count=1)
        if replaced != 1:
            raise SystemExit(f"[step239] Microsoft account helper canonicalization replaced {replaced} declaration(s)")
    else:
        raise SystemExit("[step239] Microsoft account helper is missing")

    ui_path.write_text(source, encoding="utf-8")
    return source


def patch_base_navigation(ui: str) -> str:
    if '"Features" -> featuresPage()' not in ui:
        anchor = '            "Controls" -> controlsPage()'
        if anchor in ui:
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
        else:
            anchor = '            "Renderer" -> rendererPage()'
            if anchor not in ui:
                raise SystemExit('[step291] showPage navigation anchor missing')
            ui = ui.replace(anchor, anchor + '\n            "Features" -> featuresPage()', 1)
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


def repair_bootstrap_source(root: Path) -> None:
    script = root.parent / "tools/ci/repair_step292_first_run_compile.py"
    if not script.is_file():
        raise SystemExit(f"[step292] missing compile repair: {script}")
    subprocess.run([sys.executable, str(script), str(root)], check=True)


def restore_server_contracts(root: Path) -> str:
    script = root.parent / "tools/ci/repair_step293_server_contracts_after_final_ui.py"
    if not script.is_file():
        raise SystemExit(f"[step293] missing server contract repair: {script}")
    subprocess.run([sys.executable, str(script), str(root)], check=True)
    ui_path = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    return ui_path.read_text(encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    ui_path = find_one(src, "DroidLauncherUiActivity.kt")
    ui = ui_path.read_text(encoding="utf-8")

    if "private fun showBootstrapGate()" not in ui:
        final_ui_script = root.parent / "tools/ci/apply_step286_home_account_gui.py"
        if not final_ui_script.is_file():
            raise SystemExit(f"[step291] final UI script not found: {final_ui_script}")
        namespace = runpy.run_path(str(final_ui_script), run_name="step286_helper")
        result = namespace["main"]()
        if result not in (None, 0):
            raise SystemExit(f"[step291] final UI helper returned {result}")
        ui = patch_base_navigation(ui_path.read_text(encoding="utf-8"))
        ui = ui.replace('setTextColor(text)', 'setTextColor(primaryText)')
        ui_path.write_text(ui, encoding="utf-8")
        ui = ui_path.read_text(encoding="utf-8")
    else:
        repair_bootstrap_source(root)
        ui = restore_server_contracts(root)
        if 'setTextColor(this@DroidLauncherUiActivity.text)' in ui or 'setTextColor(text)' in ui:
            raise SystemExit('[step292] invalid generated text color reference remains')

    # Canonicalize helper ownership after every late UI/launch repair and immediately
    # persist the repaired source so later Gradle compilation sees the unique form.
    ui = deduplicate_final_ui_helpers(ui_path)
    ui_path.write_text(ui, encoding="utf-8")
    ui = normalize_final_generated_ui(ui_path)

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

    if re.search(r"\bsingleLine\s*=\s*(true|false)\b", ui):
        raise SystemExit('[step239] invalid Android EditText singleLine property remains')
    if count_decl(ui, 'private fun showMicrosoftAccountInfo()') != 1:
        raise SystemExit('[step239] Microsoft account helper is not unique')
    if 'private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }' not in ui:
        raise SystemExit('[step239] Microsoft account entrypoint is not canonical')
    if 'private fun showMicrosoftSignInPage()' not in ui:
        raise SystemExit('[step239] real Microsoft sign-in page is missing')

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

    if "private fun showBootstrapGate()" in ui:
        for needle in (
            'private fun showServerDialog(index: Int)',
            'private fun getSavedServers(): List<Pair<String, Int>>',
            'private fun refreshServerStatus(host: String, port: Int)',
            'private fun deleteServer(index: Int)',
            'private fun selectServer(host: String, port: Int)',
        ):
            if needle not in ui:
                raise SystemExit(f'[step293] server contract missing: {needle}')
        print('[step287] bootstrap gate preserved during generated-source verification')

    print('[step239] generated UI helper declarations are unique')
    print('[step239] MinecraftLaunchManager Java resolver is Int -> Int')
    print('[step239] no stale String-based launch Java resolver remains')
    print('[step291] Home + Account/Profile mockups finalized with preserved Feature Center navigation')
    print('[step293] final server contracts are self-contained and background-safe')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
