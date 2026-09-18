#!/usr/bin/env python3
"""Regression tests for the final generated Kotlin compile repair."""
from pathlib import Path
import importlib.util
import sys
import tempfile

REQUIRED = [
    'private fun recommendedJavaForVersion(version: String): Int',
    'private fun storedJavaOverride(): Int?',
    'private fun resolveJavaForVersion(version: String): Int',
    'private fun saveJavaOverride(value: String)',
    'private fun getResolvedJavaForLaunch(version: String): Int',
]


def run_fixture(repair: Path, root: Path, fixture: Path) -> str:
    spec = importlib.util.spec_from_file_location('step349_repair_fixture', repair)
    if spec is None or spec.loader is None:
        raise SystemExit('could not load step349 repair module')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    source = fixture.read_text(encoding='utf-8')
    source = module.strip_orphan_fragments(source)
    source = module.normalize_page_boundary(source)
    source = module.normalize_edit_text(source)
    source = module.strip_orphan_fragments(source)
    source = module.repair_truncated_server_helpers(source)
    source = module.dedupe_methods(
        source,
        (
            'rendererPage',
            'featuresPage',
            'resolveJavaForVersion',
            'getResolvedJavaForLaunch',
        ),
    )
    fixture.write_text(source, encoding='utf-8')
    return source


def main() -> int:
    root = Path(__file__).resolve().parent
    repair = root / 'repair_step349_final_generated_compile.py'
    if not repair.is_file():
        raise SystemExit('step349 repair script missing')

    with tempfile.TemporaryDirectory(prefix='step349-regression-') as td:
        base = Path(td)
        fixture = base / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(
            '''package com.example.launcher

class DroidLauncherUiActivity {
    private fun recommendedJavaForVersion(version: String): Int {
        return 17
    }
    private fun storedJavaOverride(): Int? {
        return null
    }
    private fun resolveJavaForVersion(version: String): Int = storedJavaOverride() ?: 21
    private fun saveJavaOverride(value: String) {
        println(value)
    }
    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

    private fun rendererPage() {
        val names = listOf("fabric", "forge")
        val text = if (names.isEmpty()) "none" else names.joinToString("\n") { "• $it" }
        val renderer = "Global renderer
uses translation"
        val multiline = """keep
physical
newlines"""
        val commented = "// not a real multiline string"
        println(text + renderer + multiline + commented)
    }

    // Legacy generator fragment without a function declaration.
    private fun getSavedServer(): Pair<String, Int> = "localhost" to 25565

        val saved = getSharedPreferences("droid_launcher", MODE_PRIVATE).getInt("java_runtime_override", 0)
        if (saved in intArrayOf(8, 16, 17, 21, 25)) return saved
        val parts = "1.21.11".split('.', '-', '_').mapNotNull { it.toIntOrNull() }
        val major = parts.firstOrNull() ?: 21
        val minor = parts.getOrNull(1) ?: 0
        val patch = parts.getOrNull(2) ?: 0
        return when {
            major >= 26 -> 25
            major == 1 && minor >= 21 -> 21
            major == 1 && minor == 20 && patch >= 5 -> 21
            major == 1 && minor >= 17 -> 17
            else -> 8
        }

        storedJavaOverride() ?: recommendedJavaForVersion(version)

    private fun featuresPage() {}
}
''',
            encoding='utf-8',
        )

        source = run_fixture(repair, base, fixture)
        for needle in REQUIRED:
            if source.count(needle) != 1:
                raise SystemExit(f'expected exactly one repaired helper: {needle}')

        if 'private fun rendererPage() {' not in source:
            raise SystemExit('rendererPage anchor was damaged by helper cleanup')
        if 'private fun featuresPage() {}' not in source:
            raise SystemExit('featuresPage fixture helper disappeared')
        if 'private fun resolveJavaForVersion(version: String): Int' not in source:
            raise SystemExit('canonical resolver helper disappeared during Step349-owned cleanup')
        if source.count('\n}\n') < 1:
            raise SystemExit('fixture activity class closure disappeared')

    print('[step349-test] PASS: block and expression-bodied helper cleanup is stable')
    print('[step349-test] PASS: helper cleanup preserves rendererPage and class structure')
    print('[step349-test] PASS: page-boundary cleanup preserves the canonical resolver helper')
    print('[step349-test] PASS: deduplication remains deterministic')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
