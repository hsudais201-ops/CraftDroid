#!/usr/bin/env python3
"""Step 226: unify generated Minecraft filesystem paths on one canonical root.

Historical repair steps can rewrite the installer into several equivalent forms.
This pass deliberately matches function signatures rather than one exact body,
so later hardening does not break the generation pipeline.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step226] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def replace_function_body(text: str, signature_regex: str, replacement: str) -> tuple[str, bool]:
    pattern = re.compile(
        signature_regex + r"[\s\S]*?(?=^    (?:private|public|internal|protected) fun |^})",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        return text, False
    return text[:match.start()] + replacement.rstrip() + "\n\n" + text[match.end():], True


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    text, root_changed = replace_function_body(
        text,
        r"^    private fun minecraftRoot\(context: Context\): File =",
        '''    private fun minecraftRoot(context: Context): File =
        MinecraftStorageResolver.root(context)''',
    )
    text, version_changed = replace_function_body(
        text,
        r"^    private fun versionRoot\(context: Context, version: String\): File(?: =|\s*\{)",
        '''    private fun versionRoot(context: Context, version: String): File =
        MinecraftStorageResolver.version(context, version)''',
    )

    # Some fixtures can omit the helpers completely. Insert canonical definitions
    # once before the file-length helper; this keeps the pass idempotent.
    anchor = '    private fun fileLength(file: File): Long ='
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit('[step226] installer fileLength anchor not found')
    if 'MinecraftStorageResolver.root(context)' not in text:
        text = text[:idx] + '''    private fun minecraftRoot(context: Context): File =
        MinecraftStorageResolver.root(context)

''' + text[idx:]
        root_changed = True
    if not re.search(r"^    private fun versionRoot\(context: Context, version: String\): File\b", text, re.MULTILINE):
        idx = text.find(anchor)
        text = text[:idx] + '''    private fun versionRoot(context: Context, version: String): File =
        MinecraftStorageResolver.version(context, version)

''' + text[idx:]
        version_changed = True

    path.write_text(text, encoding="utf-8")
    print(f"[step226] installer root normalized: changed={int(root_changed)}")
    print(f"[step226] installer version root normalized: changed={int(version_changed)}")


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
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit('[step226] launch path resolver missing canonical calls: ' + ', '.join(missing))
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
    if 'MinecraftStorageResolver.root(context)' not in paths:
        raise SystemExit('[step226] launch paths missing canonical root resolver')
    if not has_version_resolver(paths):
        raise SystemExit('[step226] launch paths missing canonical version resolver')
    if not has_native_resolver(paths):
        raise SystemExit('[step226] launch paths missing canonical natives resolver')
    if 'Step 226 storage contract:' not in manager_text:
        raise SystemExit('[step226] manager missing storage contract marker')

    print('[step226] installer and launch paths now share one canonical Minecraft root')
    print('[step226] generated launch manager carries the storage contract marker')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
