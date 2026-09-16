#!/usr/bin/env python3
"""Deterministic final repair for generated launcher Kotlin."""
from pathlib import Path
import re
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
    # Defensive repair for the same corruption with different indentation.
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
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

    required_members = [
        'private fun featuresPage()',
        'private fun featureToggle(',
        'private fun homePage()',
        'private fun accountPage()',
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
    if re.search(r'(?m)^\s*(?:getSharedPreferences\("droid_launcher_servers"|serverPrefs\(\)\.getString)', source[:source.find('private fun serverPrefs()')]):
        raise SystemExit('[step349] orphan server expressions remain before helper')
    if 'singleLine =' in source:
        raise SystemExit('[step349] raw EditText singleLine assignments remain')
    if '\n            private fun ' in source:
        raise SystemExit('[step349] nested private function remains')
    if source.count('class DroidLauncherUiActivity') != 1 or not source.rstrip().endswith('}'):
        raise SystemExit('[step349] launcher class boundary invariant failed')
    if 'private var progressContext' not in inst:
        raise SystemExit('[step349] installer progressContext missing')

    print(f'[step349] final generated-source repair complete; changed={int(source != before)}')
    print('[step349] page boundary, orphan contracts, server/Java members, EditText mappings and class scope verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
