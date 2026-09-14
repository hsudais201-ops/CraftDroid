#!/usr/bin/env python3
"""Step 239: fail early on generated Kotlin helper duplication and Java type regressions."""
from pathlib import Path
import re
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

    required_manager = (
        'private fun resolveLaunchJavaRuntime(requestedJava: Int): Int',
        'javaManager.ensureRuntime(resolveLaunchJavaRuntime(requiredJava))',
    )
    for needle in required_manager:
        if needle not in manager:
            raise SystemExit(f"[step239] missing manager type-safety contract: {needle}")

    if 'resolveLaunchJavaRuntime(requestedJava: String): String' in manager:
        raise SystemExit('[step239] stale String-based launch Java resolver remains')

    if 'private fun installMinecraftVersion(version: String) {' not in ui:
        raise SystemExit('[step239] installer declaration missing')

    print('[step239] generated UI helper declarations are unique')
    print('[step239] MinecraftLaunchManager Java resolver is Int -> Int')
    print('[step239] no stale String-based Java launch resolver remains')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
