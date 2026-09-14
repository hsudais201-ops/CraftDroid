#!/usr/bin/env python3
"""Step 227: make Mojang library downloads rule-aware."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step227] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    old = '''                val lib = libraries.optJSONObject(i) ?: continue
                val libDownloads = lib.optJSONObject("downloads") ?: continue
                val artifact = libDownloads.optJSONObject("artifact")
                if (artifact != null) {
                    val path = artifact.optString("path")
                    if (path.isNotBlank()) {
                        tasks += taskFromDownload(root, File(root, "libraries/$path"), artifact, "Library $path")
                    }
                }
                val classifiers = libDownloads.optJSONObject("classifiers")
                if (classifiers != null) {
                    val keys = classifiers.keys()
                    while (keys.hasNext()) {
                        val classifier = keys.next()
                        val entry = classifiers.optJSONObject(classifier) ?: continue
                        val path = entry.optString("path")
                        if (path.isNotBlank()) {
                            tasks += taskFromDownload(root, File(root, "libraries/$path"), entry, "Native library $path")
                        }
                    }
                }
'''
    new = '''                val lib = libraries.optJSONObject(i) ?: continue
                if (!libraryAllowed(lib)) continue
                val libDownloads = lib.optJSONObject("downloads") ?: continue
                val artifact = libDownloads.optJSONObject("artifact")
                if (artifact != null) {
                    val path = artifact.optString("path")
                    if (path.isNotBlank()) {
                        tasks += taskFromDownload(root, File(root, "libraries/$path"), artifact, "Library $path")
                    }
                }
                val classifiers = libDownloads.optJSONObject("classifiers")
                if (classifiers != null) {
                    val classifier = preferredNativeClassifier(lib)
                    if (!classifier.isNullOrBlank()) {
                        val entry = classifiers.optJSONObject(classifier)
                        if (entry != null) {
                            val path = entry.optString("path")
                            if (path.isNotBlank()) {
                                tasks += taskFromDownload(root, File(root, "libraries/$path"), entry, "Native library $path")
                            }
                        }
                    }
                }
'''
    if old in text:
        text = text.replace(old, new, 1)
    elif 'if (!libraryAllowed(lib)) continue' not in text:
        raise SystemExit('[step227] library download block not found')

    if 'private fun libraryAllowed(lib: JSONObject): Boolean' not in text:
        helper = r'''
    private fun libraryAllowed(lib: JSONObject): Boolean {
        val rules = lib.optJSONArray("rules") ?: return true
        var allowed = false
        for (i in 0 until rules.length()) {
            val rule = rules.optJSONObject(i) ?: continue
            val action = rule.optString("action", "allow").equals("allow", ignoreCase = true)
            val os = rule.optJSONObject("os")
            val osName = os?.optString("name")?.trim().orEmpty()
            val arch = os?.optString("arch")?.trim().orEmpty()
            val currentOs = "linux"
            val currentArch = System.getProperty("os.arch", "").lowercase()
            val osMatches = osName.isBlank() || osName.equals(currentOs, ignoreCase = true)
            val archMatches = arch.isBlank() || currentArch.contains(arch.lowercase())
            if (osMatches && archMatches) allowed = action
        }
        return allowed
    }

    private fun preferredNativeClassifier(lib: JSONObject): String? {
        val classifiers = lib.optJSONObject("downloads")?.optJSONObject("classifiers") ?: return null
        val names = classifiers.keys().asSequence().toList()
        if (names.isEmpty()) return null
        return when {
            names.contains("natives-linux") -> "natives-linux"
            names.any { it.startsWith("natives-linux-") } -> names.first { it.startsWith("natives-linux-") }
            else -> null
        }
    }
'''
        pos = text.rfind('\n}')
        if pos < 0:
            raise SystemExit('[step227] installer class closing brace not found')
        text = text[:pos] + helper + text[pos:]

    path.write_text(text, encoding='utf-8')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    installer = find_one(root / 'app/src/main/java', 'MinecraftVersionInstallManager.kt')
    patch_installer(root)
    text = installer.read_text(encoding='utf-8')
    for needle in (
        'if (!libraryAllowed(lib)) continue',
        'private fun libraryAllowed(lib: JSONObject): Boolean',
        'private fun preferredNativeClassifier(lib: JSONObject): String?',
        'System.getProperty("os.arch", "")',
    ):
        if needle not in text:
            raise SystemExit(f'[step227] missing rule-aware installer contract: {needle}')
    print('[step227] Mojang library rules are evaluated before download')
    print('[step227] native classifier selection is limited to the preferred Linux variant')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
