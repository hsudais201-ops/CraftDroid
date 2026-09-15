#!/usr/bin/env python3
"""Step 226: unify every generated Minecraft path on one canonical storage root.

The installer may already have been hardened before this historical repair runs.
Accept both the original helper implementation and the hardened equivalent, then
normalize either form to MinecraftStorageResolver so the generation pipeline is
idempotent across all branches.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step226] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    patterns = [
        re.compile(r'''    private fun minecraftRoot\(context: Context\): File =\s*\n        File\(context\.filesDir, "minecraft"\)\.apply \{ mkdirs\(\) \}\s*\n\s*\n    private fun versionRoot\(context: Context, version: String\): File =\s*\n        File\(minecraftRoot\(context\), "versions/\$version"\)\.apply \{ mkdirs\(\) \}\s*'''),
        re.compile(r'''    private fun minecraftRoot\(context: Context\): File =\s*\n        File\(context\.filesDir, "minecraft"\)\.apply \{ mkdirs\(\) \}\s*\n\s*\n    private fun versionRoot\(context: Context, version: String\): File =\s*\n        File\(minecraftRoot\(context\), "versions/\$version"\)\.apply \{ mkdirs\(\) \}\s*'''),
    ]
    replacement = '''    private fun minecraftRoot(context: Context): File =
        MinecraftStorageResolver.root(context)

    private fun versionRoot(context: Context, version: String): File =
        MinecraftStorageResolver.version(context, version)
'''

    if 'MinecraftStorageResolver.root(context)' in text and 'MinecraftStorageResolver.version(context, version)' in text:
        pass
    else:
        changed = False
        for pattern in patterns:
            text, count = pattern.subn(replacement, text, count=1)
            if count:
                changed = True
                break
        if not changed:
            raise SystemExit('[step226] installer storage-root implementation was not found in any supported form')
    path.write_text(text, encoding="utf-8")


def has_version_resolver(text: str) -> bool:
    return 'MinecraftStorageResolver.version(context, version)' in text or 'MinecraftStorageResolver.version(context, normalized)' in text


def has_native_resolver(text: str) -> bool:
    return 'MinecraftStorageResolver.natives(context, version)' in text or 'MinecraftStorageResolver.natives(context, normalized)' in text


def patch_launch_paths(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftLaunchPaths.kt")
    text = path.read_text(encoding="utf-8")
    required = [
        'MinecraftStorageResolver.root(context)',
        'MinecraftStorageResolver.libraries(context)',
        'MinecraftStorageResolver.assets(context)',
    ]
    for needle in required:
        if needle not in text:
            raise SystemExit(f'[step226] launch path resolver missing canonical call: {needle}')
    if not has_version_resolver(text):
        raise SystemExit('[step226] launch path resolver missing canonical version call')
    if not has_native_resolver(text):
        raise SystemExit('[step226] launch path resolver missing canonical natives call')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    if not (root / "app/src/main/java").is_dir():
        raise SystemExit(f"[step226] Android source directory not found: {root}")
    patch_installer(root)
    patch_launch_paths(root)

    manager = find_one(root / "app/src/main/java", "MinecraftLaunchManager.kt")
    manager_text = manager.read_text(encoding="utf-8")
    marker = '// Step 226 storage contract: Minecraft artifacts and launch paths share MinecraftStorageResolver.\n'
    if 'Step 226 storage contract:' not in manager_text:
        manager.write_text(marker + manager_text, encoding="utf-8")
        manager_text = marker + manager_text

    installer = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt").read_text(encoding="utf-8")
    paths = find_one(root / "app/src/main/java", "MinecraftLaunchPaths.kt").read_text(encoding="utf-8")
    if 'MinecraftStorageResolver.root(context)' not in installer:
        raise SystemExit('[step226] installer missing canonical root resolver')
    if not has_version_resolver(installer):
        raise SystemExit('[step226] installer missing canonical version resolver')
    for needle in ('MinecraftStorageResolver.root(context)', 'MinecraftStorageResolver.libraries(context)', 'MinecraftStorageResolver.assets(context)'):
        if needle not in paths:
            raise SystemExit(f'[step226] launch paths missing storage contract: {needle}')
    if not has_version_resolver(paths):
        raise SystemExit('[step226] launch paths missing canonical version resolver')
    if not has_native_resolver(paths):
        raise SystemExit('[step226] launch paths missing canonical natives resolver')
    if 'Step 226 storage contract:' not in manager_text:
        raise SystemExit('[step226] manager missing storage contract marker')

    print('[step226] installer and launch-path code now share one canonical Minecraft root')
    print('[step226] generated launch manager carries the Step 226 storage contract marker')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
