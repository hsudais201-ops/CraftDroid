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
    state = 'code'; escaped = False; i = brace
    while i < len(text):
        c = text[i]; n = text[i + 1] if i + 1 < len(text) else ''; n2 = text[i + 2] if i + 2 < len(text) else ''
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
        text = text.replace(bad, '    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n    private fun featuresPage() {', 1)
    pattern = re.compile(r'(?s)    private fun getResolvedJavaForLaunch\(version: String\): Int \{\s*private fun featuresPage\(\) \{')
    return pattern.sub('    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)\n\n    private fun featuresPage() {', text, count=1)


def normalize_edit_text(text: str) -> str:
    # Apply the real Android View API after every late UI generator has run.
    text = re.sub(r'\bsingleLine\s*=\s*true\b', 'setSingleLine(true)', text)
    text = re.sub(r'\bsingleLine\s*=\s*false\b', 'setSingleLine(false)', text)
    return text


def repair_truncated_server_helpers(text: str) -> str:
    text = text.replace(
        'private fun serverPrefs(): android.content.SharedPreferences =\nprivate fun getSavedServers()',
        '    private fun serverPrefs(): android.content.SharedPreferences =\n        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n\n    private fun getSavedServers()'
    )
    text = text.replace(
        'private fun getServerName(index: Int): String =\nprivate fun getServerStatus(host: String, port: Int): String =',
        '    private fun getServerName(index: Int): String {\n        val prefs = serverPrefs()\n        val count = prefs.getInt("count", 0).coerceIn(0, 256)\n        if (index !in 0 until count) return "Server $index"\n        return prefs.getString("name_$index", "Server $index")?.trim().orEmpty().ifBlank { "Server $index" }\n    }\n\n    private fun getServerStatus(host: String, port: Int): String ='
    )
    for name in ('getSavedServers', 'getServerName', 'getServerStatus', 'selectServer', 'deleteServer', 'showServerDialog', 'refreshServerStatus'):
        text = re.sub(r'(?m)^private fun ' + re.escape(name) + r'\b', '    private fun ' + name, text)
    return text


def normalize_on_create(text: str) -> str:
    start = text.find('    override fun onCreate(')
    if start < 0: raise SystemExit('[step349] onCreate not found')
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
    if declaration in text: return text
    anchors = ('    private val cancellations = ConcurrentHashMap.newKeySet<String>()', '    private val activeTasks = ConcurrentHashMap<String, Job>()', '    private val taskStates = ConcurrentHashMap<String, Any>()')
    for anchor in anchors:
        if anchor in text: return text.replace(anchor, anchor + '\n' + declaration, 1)
    match = re.search(r'class\s+MinecraftVersionInstallManager\b[^\{]*\{', text)
    if match: return text[:match.end()] + '\n' + declaration + '\n' + text[match.end():]
    raise SystemExit('[step349] cannot locate installer class field insertion point')


def repair_real_cosmetic_picker(text: str) -> str:
    """Ensure skin/cape selection uses the Android document picker and persists the URI."""
    required = ('microsoft_skin_uri', 'microsoft_cape_uri', 'resultCode != RESULT_OK', 'contentResolver.takePersistableUriPermission')
    if all(token in text for token in required):
        return text
    anchor = '        super.onActivityResult(requestCode, resultCode, data)\n'
    if anchor not in text:
        raise SystemExit('[step349] onActivityResult anchor missing for real cosmetic picker')
    callback = '''        if (requestCode == 3371 || requestCode == 3372) {
            if (resultCode != RESULT_OK) return
            val uri = data?.data ?: return
            try {
                contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
            } catch (_: Throwable) {
                // Some document providers do not support persistable permissions.
            }
            val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
            getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
                .edit()
                .putString(key, uri.toString())
                .apply()
            android.widget.Toast.makeText(
                this,
                if (requestCode == 3371) "Skin image selected and saved" else "Cape image selected and saved",
                android.widget.Toast.LENGTH_SHORT
            ).show()
            showMicrosoftSignInPage()
            return
        }
'''
    return text.replace(anchor, anchor + callback + '        // STEP352_REAL_COSMETIC_PICKER_CALLBACK\n', 1)


def run_quality_gate(repo_root: Path, generated_root: Path) -> None:
    checker = repo_root / 'tools/ci/deep_quality_pass_1000.py'
    if checker.is_file():
        subprocess.run([sys.executable, str(checker), str(generated_root)], cwd=repo_root, check=True)
        print('[step349] deep_quality_pass_1000 PASS')


def assert_final_ui_invariants(source: str) -> None:
    required_members = ('private fun featuresPage()','private fun featureToggle(','private fun rendererPage()','private fun javaPage()','private fun controlsPage()','private fun libraryPage(','private fun aboutPage(','private fun serverPrefs()','private fun getSavedServers()','private fun getServerName(','private fun getServerStatus(','private fun selectServer(','private fun deleteServer(','private fun showServerDialog(','private fun refreshServerStatus(','private fun resolveJavaForVersion(','private fun getResolvedJavaForLaunch(')
    for sig in required_members:
        if source.count(sig) != 1: raise SystemExit(f'[step349] {sig} count={source.count(sig)}, expected 1')
    if 'private fun featuresPage() {' not in source: raise SystemExit('[step349] Feature Center method body missing')
    if any(x in source for x in ('STEP293_SERVER_CONTRACTS','STEP329_SERVER_CONTRACTS')): raise SystemExit('[step349] orphan contract markers remain')
    if 'singleLine =' in source: raise SystemExit('[step349] invalid singleLine property remains')
    if '\nprivate fun ' in source: raise SystemExit('[step349] top-level private helper remains outside class')
    start = source.find('override fun onCreate')
    slice_ = source[start:start+700]
    if 'showBootstrapGate()' in slice_ or 'buildUi()\n        showPage("Game")' not in slice_: raise SystemExit('[step349] direct launcher startup invariant failed')
    if source.count('class DroidLauncherUiActivity') != 1 or not source.rstrip().endswith('}'): raise SystemExit('[step349] launcher class boundary invariant failed')
    if 'STEP352_REAL_COSMETIC_PICKER_CALLBACK' not in source: raise SystemExit('[step349] real skin/cape picker callback missing')
    if 'microsoft_skin_uri' not in source or 'microsoft_cape_uri' not in source: raise SystemExit('[step349] cosmetic URI persistence missing')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    repo_root = Path.cwd().resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    installer = root / 'app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt'
    if not ui.is_file() or not installer.is_file(): raise SystemExit('[step349] required generated sources are missing')
    source = ui.read_text(encoding='utf-8')
    before = source
    source = strip_orphan_fragments(source)
    source = normalize_page_boundary(source)
    source = normalize_edit_text(source)
    source = strip_orphan_fragments(source)
    source = repair_truncated_server_helpers(source)
    source = dedupe_methods(source, ('featuresPage','featureToggle','rendererPage','javaPage','controlsPage','libraryPage','aboutPage','serverPrefs','getSavedServers','getServerName','getServerStatus','selectServer','deleteServer','showServerDialog','refreshServerStatus','resolveJavaForVersion','getResolvedJavaForLaunch'))
    source = normalize_on_create(source)
    source = repair_real_cosmetic_picker(source)
    source = normalize_edit_text(source)
    ui.write_text(source, encoding='utf-8')
    inst_before = installer.read_text(encoding='utf-8')
    inst = repair_progress_context(inst_before)
    installer.write_text(inst, encoding='utf-8')
    navigation = repo_root / 'tools/ci/repair_step295_final_navigation.py'
    if not navigation.is_file(): raise SystemExit('[step349] final Feature Center navigation repair script is missing')
    subprocess.run([sys.executable, str(navigation), str(root)], cwd=repo_root, check=True)
    # Step 295 is itself a late UI generator and can reintroduce code patterns
    # normalized above. Re-read and normalize again immediately before the
    # invariants and quality gate so the generated tree matches what Gradle sees.
    source = ui.read_text(encoding='utf-8')
    source = strip_orphan_fragments(source)
    source = normalize_page_boundary(source)
    source = normalize_edit_text(source)
    source = repair_truncated_server_helpers(source)
    source = dedupe_methods(source, ('featuresPage','featureToggle','rendererPage','javaPage','controlsPage','libraryPage','aboutPage','serverPrefs','getSavedServers','getServerName','getServerStatus','selectServer','deleteServer','showServerDialog','refreshServerStatus','resolveJavaForVersion','getResolvedJavaForLaunch'))
    source = repair_real_cosmetic_picker(source)
    source = normalize_edit_text(source)
    ui.write_text(source, encoding='utf-8')
    source = ui.read_text(encoding='utf-8')
    assert_final_ui_invariants(source)
    if 'private var progressContext: android.content.Context? = null' not in inst: raise SystemExit('[step349] installer progressContext declaration missing')
    if '"Features" -> featuresPage()' not in source or 'setOnClickListener { showPage("Features") }' not in source: raise SystemExit('[step349] Feature Center navigation not restored at final boundary')
    run_quality_gate(repo_root, root)
    print(f'[step349] final repair complete; ui_changed={int(source != before)} installer_changed={int(inst != inst_before)}')
    return 0


if __name__ == '__main__': raise SystemExit(main())
