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


def dedupe_methods(text: str, names: tuple[str, ...]) -> str:
    for name in names:
        pat = re.compile(r'(?m)^\s*private\s+fun\s+' + re.escape(name) + r'\s*\(')
        while True:
            matches = list(pat.finditer(text))
            if len(matches) <= 1:
                break
            m = matches[0]
            text = text[:m.start()] + text[method_end(text, m.start()):]
    return text


def normalize_page_boundary(text: str) -> str:
    bad = '    private fun getResolvedJavaForLaunch(version: String): Int {\n            private fun featuresPage() {'
    if bad in text:
        text = text.replace(
            bad,
            '    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n    private fun featuresPage() {',
            1,
        )
    pattern = re.compile(
        r'(?s)    private fun getResolvedJavaForLaunch\(version: String\): Int \{\s*'
        r'private fun featuresPage\(\) \{'
    )
    return pattern.sub(
        '    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n'
        '    private fun featuresPage() {',
        text,
        count=1,
    )


def normalize_edit_text(text: str) -> str:
    return text.replace('singleLine = true', 'setSingleLine(true)').replace(
        'singleLine = false', 'setSingleLine(false)'
    )


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


def repair_progress_context(text: str) -> str:
    declaration = '    private var progressContext: android.content.Context? = null'
    if declaration in text:
        return text
    anchors = (
        '    private val cancellations = ConcurrentHashMap.newKeySet<String>()',
        '    private val activeTasks = ConcurrentHashMap<String, Job>()',
        '    private val taskStates = ConcurrentHashMap<String, Any>()',
    )
    for anchor in anchors:
        if anchor in text:
            return text.replace(anchor, anchor + '\n' + declaration, 1)
    match = re.search(r'class\s+MinecraftVersionInstallManager\b[^\{]*\{', text)
    if match:
        return text[:match.end()] + '\n' + declaration + '\n' + text[match.end():]
    raise SystemExit('[step349] cannot locate installer class field insertion point')


def run_quality_gate(repo_root: Path, generated_root: Path) -> None:
    checker = repo_root / 'tools/ci/deep_quality_pass_1000.py'
    if checker.is_file():
        subprocess.run([sys.executable, str(checker), str(generated_root)], cwd=repo_root, check=True)
        print('[step349] deep_quality_pass_1000 PASS')
    else:
        print('[step349] deep_quality_pass_1000.py not present; structural gate still active')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    repo_root = Path.cwd().resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    installer = root / 'app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt'
    if not ui.is_file() or not installer.is_file():
        raise SystemExit('[step349] required generated sources are missing')

    source = ui.read_text(encoding='utf-8')
    before = source
    source = strip_orphan_fragments(source)
    source = normalize_page_boundary(source)
    source = normalize_edit_text(source)
    source = strip_orphan_fragments(source)
    source = dedupe_methods(source, (
        'featuresPage', 'featureToggle', 'rendererPage', 'javaPage', 'controlsPage',
        'libraryPage', 'aboutPage', 'serverPrefs', 'getSavedServers', 'getServerName',
        'getServerStatus', 'selectServer', 'deleteServer', 'showServerDialog',
        'refreshServerStatus', 'resolveJavaForVersion', 'getResolvedJavaForLaunch',
    ))
    source = normalize_on_create(source)
    ui.write_text(source, encoding='utf-8')

    inst_before = installer.read_text(encoding='utf-8')
    inst = repair_progress_context(inst_before)
    installer.write_text(inst, encoding='utf-8')

    required_members = (
        'private fun featuresPage()', 'private fun featureToggle(', 'private fun rendererPage()',
        'private fun javaPage()', 'private fun controlsPage()', 'private fun libraryPage(',
        'private fun aboutPage(', 'private fun serverPrefs()', 'private fun getSavedServers()',
        'private fun getServerName(', 'private fun getServerStatus(', 'private fun selectServer(',
        'private fun deleteServer(', 'private fun showServerDialog(', 'private fun refreshServerStatus(',
        'private fun resolveJavaForVersion(', 'private fun getResolvedJavaForLaunch(',
    )
    for sig in required_members:
        if source.count(sig) != 1:
            raise SystemExit(f'[step349] {sig} count={source.count(sig)}, expected 1')
    if 'private fun featuresPage() {\n        pageArea.addView(section("Feature Center"' not in source:
        raise SystemExit('[step349] Feature Center method body boundary failed')
    if any(x in source for x in ('STEP293_SERVER_CONTRACTS', 'STEP329_SERVER_CONTRACTS')):
        raise SystemExit('[step349] orphan contract markers remain')
    server_anchor = source.find('private fun serverPrefs()')
    if re.search(r'(?m)^\s*(?:getSharedPreferences\("droid_launcher_servers"|serverPrefs\(\)\.getString)', source[:server_anchor]):
        raise SystemExit('[step349] orphan server expressions remain before helper')
    if 'singleLine =' in source or '\n            private fun ' in source:
        raise SystemExit('[step349] invalid generated Kotlin scope/API remains')
    start = source.find('override fun onCreate')
    slice_ = source[start:start + 700]
    if 'showBootstrapGate()' in slice_ or 'buildUi()\n        showPage("Game")' not in slice_:
        raise SystemExit('[step349] direct launcher startup invariant failed')
    if source.count('class DroidLauncherUiActivity') != 1 or not source.rstrip().endswith('}'):
        raise SystemExit('[step349] launcher class boundary invariant failed')
    if 'private var progressContext: android.content.Context? = null' not in inst:
        raise SystemExit('[step349] installer progressContext declaration missing')

    # Final late-generation writers can replace buildUi/showPage after Step295.
    # Reapply the idempotent navigation repair immediately before the quality gate.
    navigation = repo_root / 'tools/ci/repair_step295_final_navigation.py'
    if navigation.is_file():
        subprocess.run([sys.executable, str(navigation), str(root)], cwd=repo_root, check=True)
        source = ui.read_text(encoding='utf-8')
        if '"Features" -> featuresPage()' not in source or 'setOnClickListener { showPage("Features") }' not in source:
            raise SystemExit('[step349] Feature Center navigation was not restored at final boundary')
    else:
        raise SystemExit('[step349] final Feature Center navigation repair script is missing')

    run_quality_gate(repo_root, root)
    print(f'[step349] final repair complete; ui_changed={int(source != before)} installer_changed={int(inst != inst_before)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
