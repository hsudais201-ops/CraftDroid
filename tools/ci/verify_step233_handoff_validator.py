#!/usr/bin/env python3
"""Step 233: verify the secure Minecraft launch handoff validator source contract."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step233] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    validator = find_one(root / "app/src/main/java", "MinecraftLaunchHandoffValidator.kt")
    handoff = find_one(root / "app/src/main/java", "MinecraftLaunchHandoff.kt")
    storage = find_one(root / "app/src/main/java", "MinecraftStorageResolver.kt")
    v = validator.read_text(encoding="utf-8")
    h = handoff.read_text(encoding="utf-8")
    s = storage.read_text(encoding="utf-8")
    checks = [
        (v, "object MinecraftLaunchHandoffValidator"),
        (v, "fun validate(context: Context, handoff: MinecraftLaunchHandoff): String?"),
        (v, "MinecraftStorageResolver.root(context)"),
        (v, "MinecraftStorageResolver.version(context, handoff.version)"),
        (v, "MinecraftStorageResolver.libraries(context)"),
        (v, "MinecraftStorageResolver.assets(context)"),
        (v, "MinecraftStorageResolver.natives(context, handoff.version)"),
        (v, "canonicalFile"),
        (v, "classpath.any"),
        (v, "classpath.none"),
        (h, "object MinecraftLaunchHandoffReader"),
        (s, "object MinecraftStorageResolver"),
    ]
    for text, needle in checks:
        if needle not in text:
            raise SystemExit(f"[step233] missing: {needle}")
    print("Step 233 secure handoff validator verification: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
