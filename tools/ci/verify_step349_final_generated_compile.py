#!/usr/bin/env python3
"""Regression tests for the final generated Kotlin compile repair."""
from pathlib import Path
import subprocess
import sys
import tempfile

REQUIRED = [
    'private fun recommendedJavaForVersion(version: String): Int',
    'private fun storedJavaOverride(): Int?',
    'private fun resolveJavaForVersion(version: String): Int',
    'private fun saveJavaOverride(value: String)',
    'private fun getResolvedJavaForLaunch(version: String): Int',
]


def run_fixture(repair: Path, fixture: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(repair), str(fixture.parents[4])],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f'step349 fixture execution failed:\n{result.stdout}\n{result.stderr}')
    return fixture.read_text(encoding='utf-8')


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
}
''',
            encoding='utf-8',
        )

        source = run_fixture(repair, fixture)
        for needle in REQUIRED:
            if source.count(needle) != 1:
                raise SystemExit(f'expected exactly one repaired helper: {needle}')

        if 'names.joinToString("\\n") { "• $it" }' not in source:
            raise SystemExit('escaped dependency join contract missing after repair')
        if 'val renderer = "Global renderer\\nuses translation"' not in source:
            raise SystemExit('ordinary multiline renderer string was not escaped')
        if 'val renderer = "Global renderer\nuses translation"' in source:
            raise SystemExit('literal newline remains inside renderer Kotlin string')
        if 'val multiline = """keep\nphysical\nnewlines"""' not in source:
            raise SystemExit('triple-quoted multiline string was damaged')
        if 'private fun rendererPage() {' not in source:
            raise SystemExit('rendererPage anchor was damaged by helper cleanup')

    print('[step349-test] PASS: block and expression-bodied helper cleanup is stable')
    print('[step349-test] PASS: malformed dependency join is escaped correctly')
    print('[step358-test] PASS: ordinary multiline Kotlin strings are escaped correctly')
    print('[step358-test] PASS: triple-quoted Kotlin multiline strings are preserved')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
