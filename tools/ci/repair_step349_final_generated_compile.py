#!/usr/bin/env python3
"""Deterministic final repair for generated launcher Kotlin."""
from pathlib import Path
import re
import subprocess
import sys


def strip_orphan_fragments(text: str) -> str:
    patterns = [
        r'(?m)^\s*//\s*STEP(?:293|329)_SERVER_CONTRACTS\s*$\n?',
        r'(?m)^\s*getSharedPreferences\("droid_launcher_servers", MODE_PRIVATE\)\s*$\n?',
        r'(?m)^\s*serverPrefs\(\)\.getString\("name_\$index", ""\)\?\.trim\(\)\.orEmpty\(\)\s*$\n?',
        r'(?m)^\s*serverPrefs\(\)\.getString\("status_\$\{host\}:\$port", "Unknown"\) \?: "Unknown"\s*$\n?',
    ]
    for pattern in patterns:
        text = re.sub(pattern, '', text)
    return text


def normalize_page_boundary(text: str) -> str:
    bad = '    private fun getResolvedJavaForLaunch(version: String): Int {\n            private fun featuresPage() {'
    if bad in text:
        return text.replace(
            bad,
            '    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n    private fun featuresPage() {',
            1,
        )
    pattern = re.compile(
        r'(?s)    private fun getResolvedJavaForLaunch\(version: String\): Int \{\s*'
        r'private fun featuresPage\(\) \{'
    )
    if pattern.search(text):
        text = pattern.sub(
            '    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n'
            '    private fun featuresPage() {',
            text,
            count=1,
        )
    return text


def normalize_edit_text(text: str) -> str:
    return text.replace('singleLine = true', 'setSingleLine(true)').replace(
        'singleLine = false', 'setSingleLine(false)'
    )


def method_end(text: str, start: int) -> int:
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('[step349] method opening brace missing')
    depth = 0
    state = 'code'
    escaped = False
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        n2 = text[i + 2] if i + 2 < len(text) else ''
        if state == 'line':
            if c == '\n': state = 'code'
            i += 1; continue
        if state == 'block':
            if c == '*' and n == '/': state = 'code'; i += 2
            else: i += 1
            continue
        if state == 'triple':
            if c == '"' and n == '"' and n2 == '"': state = 'code'; i += 3
            else: i += 1
            continue
        if state == 'string':
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': state = 'code'
            i += 1; continue
        if state == 'char':
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == "'": state = 'code'
            i += 1; continue
        if c == '/' and n == '/': state = 'line'; i += 2; continue
        if c == '/' and n == '*': state = 'block'; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = 'triple'; i += 3; continue
        if c == '"': state = 'string'; i += 1; continue
        if c == "'": state = 'char'; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise SystemExit('[step349] unterminated method')


def normalize_on_create(text: str) -> str:
    start = text.find('    override fun onCreate(')
    if start < 0:
        raise SystemExit('[step349] onCreate not found')
    end = method_end(text, start)
    replacement = '''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        buildUi()
        showPage("Game")
    }'''
    return text[:start] + replacement + text[end:]


def run_quality_gate(repo_root: Path, generated_root: Path) -> None:
    checker = repo_root / 'tools/ci/deep_quality_pass_1000.py'
    if not checker.is_file():
        print('[step349] deep_quality_pass_1000.py not present; continuing with structural gate')
        return
    subprocess.run([sys.executable, str(checker), str(generated_root)], cwd=repo_root, check=True)
    print('[step349] deep_quality_pass_1000 PASS')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    repo_root = Path.cwd().resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    installer = root / 'app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt'
    if not ui.is_file():
        raise SystemExit(f'[step349] missing UI source: {ui}')
    if not installer.is_file():
        raise SystemExit(f'[step349] missing installer source: {installer}')

    source = ui.read_text(encoding='utf-8')
    before = source
    source = strip_orphan_fragments(source)
    source = normalize_page_boundary(source)
    source = normalize_edit_text(source)
    source = strip_orphan_fragments(source)
    source = normalize_on_create(source)
    ui.write_text(source, encoding='utf-8')

    inst = installer.read_text(encoding='utf-8')
    if 'progressContext' not in inst:
        anchor = '    private val cancellations = ConcurrentHashMap.newKeySet<String>()'
        if anchor not in inst:
            raise SystemExit('[step349] installer cancellation anchor missing')
        inst = inst.replace(
            anchor,
            anchor + '\n    private var progressContext: android.content.Context? = null',
            1,
        )
        installer.write_text(inst, encoding='utf-8')

    # Verify members that are actually generated by the current UI builder.
    required_members = [
        'private fun featuresPage()',
        'private fun featureToggle(',
        'private fun rendererPage()',
        'private fun javaPage()',
        'private fun controlsPage()',
        'private fun libraryPage(',
        'private fun aboutPage(',
        'private fun serverPrefs()',
        'private fun getSavedServers()',
        'private fun getServerName(',
        'private fun getServerStatus(',
        'private fun selectServer(',
        'private fun deleteServer(',
        'private fun showServerDialog(',
        'private fun refreshServerStatus(',
        'private fun resolveJavaForVersion(',
        'private fun getResolvedJavaForLaunch(',
    ]
    for sig in required_members:
        count = source.count(sig)
        if count != 1:
            raise SystemExit(f'[step349] {sig} count={count}, expected 1')
    if 'private fun featuresPage() {\n        pageArea.addView(section("Feature Center"' not in source:
        raise SystemExit('[step349] Feature Center method body boundary failed')
    if 'STEP293_SERVER_CONTRACTS' in source or 'STEP329_SERVER_CONTRACTS' in source:
        raise SystemExit('[step349] orphan contract markers remain')
    server_anchor = source.find('private fun serverPrefs()')
    if server_anchor < 0:
        raise SystemExit('[step349] serverPrefs anchor missing')
    if re.search(r'(?m)^\s*(?:getSharedPreferences\("droid_launcher_servers"|serverPrefs\(\)\.getString)', source[:server_anchor]):
        raise SystemExit('[step349] orphan server expressions remain before helper')
    if 'singleLine =' in source:
        raise SystemExit('[step349] raw EditText singleLine assignments remain')
    if '\n            private fun ' in source:
        raise SystemExit('[step349] nested private function remains')
    create_start = source.find('override fun onCreate')
    create_slice = source[create_start:create_start + 700]
    if 'showBootstrapGate()' in create_slice:
        raise SystemExit('[step349] fake bootstrap gate is still in onCreate')
    if 'buildUi()\n        showPage("Game")' not in create_slice:
        raise SystemExit('[step349] direct Game startup invariant missing')
    if source.count('class DroidLauncherUiActivity') != 1 or not source.rstrip().endswith('}'):
        raise SystemExit('[step349] launcher class boundary invariant failed')
    if 'private var progressContext' not in inst:
        raise SystemExit('[step349] installer progressContext missing')

    run_quality_gate(repo_root, root)
    print(f'[step349] final generated-source repair complete; changed={int(source != before)}')
    print('[step349] page boundary, startup, orphan contracts, generated members, EditText mappings and class scope verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
