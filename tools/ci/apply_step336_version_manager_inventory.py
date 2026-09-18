#!/usr/bin/env python3
"""Step 336: expose the installed-version inventory to the generated Home selector."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    hits = list((root / "app/src/main/java").rglob("MinecraftVersionInstallManager.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step336] expected one MinecraftVersionInstallManager.kt, found {len(hits)}")
    path = hits[0]
    source = path.read_text(encoding="utf-8")
    marker = "    fun lastError(context: Context, version: String): String? =\n"
    if "fun installedVersions(context: Context): List<String>" not in source:
        helper = '''    /** Returns version directories that contain a verified Minecraft client JAR + metadata. */
    fun installedVersions(context: Context): List<String> {
        val versionsDir = File(minecraftRoot(context), "versions")
        val entries = versionsDir.listFiles() ?: return emptyList()
        return entries.asSequence()
            .filter { it.isDirectory }
            .map { it.name }
            .filter { isInstalled(context, it) }
            .distinct()
            .sortedDescending()
            .toList()
    }

'''
        if marker in source:
            source = source.replace(marker, helper + marker, 1)
        elif "\n}" in source:
            # Current manager variant has no lastError method. Insert the same
            # real inventory API immediately before the single class terminator.
            pos = source.rfind("\n}")
            source = source[:pos] + "\n" + helper.rstrip("\n") + source[pos:]
        else:
            raise SystemExit("[step336] no safe insertion point for installedVersions")
    if source.count("fun installedVersions(context: Context): List<String>") != 1:
        raise SystemExit("[step336] installedVersions declaration count is not exactly one")
    path.write_text(source, encoding="utf-8")
    print("[step336] installed Minecraft version inventory exposed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
