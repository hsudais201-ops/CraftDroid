#!/usr/bin/env python3
"""Step 320 verification for modern Minecraft/runtime/content support."""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    java = find_one(root / "app/src/main/java", "MinecraftRuntimeProfile.kt").read_text(encoding="utf-8")
    latest = find_one(root / "app/src/main/java", "MinecraftLatestVersionManager.kt").read_text(encoding="utf-8")
    content = find_one(root / "app/src/main/java", "MinecraftContentManager.kt").read_text(encoding="utf-8")
    bg = find_one(root / "app/src/main/java", "LauncherBackgroundInstallController.kt").read_text(encoding="utf-8")
    updater = find_one(root / "app/src/main/java", "DroidLauncherUpdateManager.kt").read_text(encoding="utf-8")

    required_java_contracts = [
        'first >= 26 -> Profile(25',
        'major in setOf(8, 16, 17, 21, 25)',
        'requiresJava25',
    ]
    for needle in required_java_contracts:
        if needle not in java:
            raise SystemExit(f"Missing Java 25 contract: {needle}")

    for needle in ('version_manifest_v2.json', 'optJSONObject("latest")', 'https://'):
        if needle not in latest:
            raise SystemExit(f"Missing latest-version contract: {needle}")

    for needle in ('MODPACK', 'MOD', 'SHADER', 'RESOURCE_PACK', 'WORLD', 'ZipInputStream', 'Unsafe ZIP entry'):
        if needle not in content:
            raise SystemExit(f"Missing content contract: {needle}")

    for needle in ('CountDownLatch', 'Kind.MINECRAFT_VERSION', 'State.SUCCESS', 'State.FAILED'):
        if needle not in bg:
            raise SystemExit(f"Missing background-install contract: {needle}")

    for needle in ('releases/latest', '.apk', '.sha256', 'SHA-256 verification failed'):
        if needle not in updater:
            raise SystemExit(f"Missing updater trust contract: {needle}")

    # Reject accidental legacy-only runtime lists in the new policy.
    if re.search(r'setOf\(8\s*,\s*16\s*,\s*17\s*,\s*21\s*\)', java):
        raise SystemExit("Modern runtime policy dropped Java 25")

    print('[step320] Java 25, authoritative latest-version, content libraries, background install, and signed updater contracts PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
