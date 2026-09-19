#!/usr/bin/env python3
"""Step 227: make Mojang library downloads rule-aware and Android-native bounded."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step227] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def find_matching_brace(text: str, opening: int) -> int:
    depth = 0
    quote = None
    escaped = False
    for i in range(opening, len(text)):
        ch = text[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ('"', "'"):
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def remove_method(text: str, signature: str) -> str:
    start = text.find(signature)
    if start < 0:
        return text
    opening = text.find("{", start)
    if opening < 0:
        raise SystemExit(f"[step227] method opening brace missing: {signature}")
    end = find_matching_brace(text, opening)
    if end < 0:
        raise SystemExit(f"[step227] unbalanced method braces: {signature}")
    end += 1
    while end < len(text) and text[end] == "\n":
        end += 1
    return text[:start] + text[end:]


HELPERS = '''    private fun libraryAllowed(lib: JSONObject): Boolean {
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


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    lib_marker = '                val lib = libraries.optJSONObject(i) ?: continue'
    if lib_marker not in text:
        raise SystemExit("[step227] library loop marker not found")
    if 'if (!libraryAllowed(lib)) continue' not in text:
        text = text.replace(
            lib_marker,
            lib_marker + "\n                if (!libraryAllowed(lib)) continue",
            1,
        )

    classifiers_start = text.find('                val classifiers = libDownloads.optJSONObject("classifiers")')
    if classifiers_start >= 0 and 'val classifier = preferredNativeClassifier(lib)' not in text[classifiers_start:classifiers_start + 2500]:
        if_start = text.find("if (classifiers != null)", classifiers_start)
        if if_start < 0:
            raise SystemExit("[step227] classifiers condition missing")
        opening = text.find("{", if_start)
        end = find_matching_brace(text, opening) if opening >= 0 else -1
        if end < 0:
            raise SystemExit("[step227] classifiers block braces are unbalanced")
        targeted = '''                val classifiers = libDownloads.optJSONObject("classifiers")
                if (classifiers != null) {
                    val classifier = preferredNativeClassifier(lib)
                    if (!classifier.isNullOrBlank()) {
                        val entry = classifiers.optJSONObject(classifier)
                        if (entry != null) {
                            val path = entry.optString("path")
                            if (path.isNotBlank()) {
                                tasks += taskFromDownload(
                                    root,
                                    File(root, "libraries/$path"),
                                    entry,
                                    "Native library $path"
                                )
                            }
                        }
                    }
                }
'''
        text = text[:classifiers_start] + targeted + text[end + 1:]
    elif classifiers_start < 0 and 'val classifier = preferredNativeClassifier(lib)' not in text:
        raise SystemExit("[step227] no classifier block found to constrain")

    # Remove existing helper copies using balanced braces, then install one canonical copy.
    text = remove_method(text, '    private fun libraryAllowed(lib: JSONObject): Boolean')
    text = remove_method(text, '    private fun preferredNativeClassifier(lib: JSONObject): String?')

    pos = text.rfind("\n}")
    if pos < 0:
        raise SystemExit("[step227] installer class closing brace not found")
    text = text[:pos] + HELPERS + text[pos:]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    installer = find_one(root / 'app/src/main/java', 'MinecraftVersionInstallManager.kt')
    patch_installer(root)
    text = installer.read_text(encoding='utf-8')
    for needle in (
        'if (!libraryAllowed(lib)) continue',
        'private fun libraryAllowed(lib: JSONObject): Boolean',
        'private fun preferredNativeClassifier(lib: JSONObject): String?',
        'val classifier = preferredNativeClassifier(lib)',
        'System.getProperty("os.arch", "")',
    ):
        if needle not in text:
            raise SystemExit(f'[step227] missing rule-aware installer contract: {needle}')
    print('[step227] Mojang library rules are evaluated before download')
    print('[step227] native classifier selection is limited to the preferred Linux variant')
    print('[step227] structure-tolerant repair anchors applied')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
