#!/usr/bin/env python3
"""Step 328: wire the authoritative Mojang latest release into the final UI.

The UI is generated repeatedly by older repair stages, so this final pass edits
only stable function bodies and remains idempotent. It never replaces Mojang's
manifest resolver with a hard-coded current release.
"""
from pathlib import Path
import re
import sys

FALLBACK = "26.3"


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step328] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def replace_function(source: str, signature: str, replacement: str) -> str:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step328] missing function signature: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step328] missing function body: {signature}")
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[:start] + replacement + source[i + 1:]
    raise SystemExit(f"[step328] unterminated function: {signature}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    manager = find_one(root / "app/src/main/java", "MinecraftLatestVersionManager.kt")
    if "object MinecraftLatestVersionManager" not in manager.read_text(encoding="utf-8"):
        raise SystemExit("[step328] latest-version manager implementation missing")

    source = ui.read_text(encoding="utf-8")
    selected_sig = "    private fun selectedMinecraftVersion(): String"
    selected = '''    private fun selectedMinecraftVersion(): String {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        return prefs.getString("selected_minecraft_version", null)?.trim()?.takeIf { it.isNotBlank() }
            ?: MinecraftLatestVersionManager.getCached(this)
            ?: FALLBACK
    }
'''
    if selected_sig in source:
        source = replace_function(source, selected_sig, selected)

    refresh = '''    private fun refreshLatestMinecraftVersion() {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val explicitlySelected = prefs.contains("selected_minecraft_version")
        MinecraftLatestVersionManager.refresh(this) { latest ->
            val id = latest?.id?.trim().orEmpty()
            if (id.isNotEmpty()) {
                val editor = getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                    .putString("latest_minecraft_version", id)
                if (!explicitlySelected) {
                    editor.putString("selected_minecraft_version", id)
                }
                editor.apply()
                if (!explicitlySelected && currentPage == "Game") {
                    showPage("Game")
                }
            }
        }
    }

'''
    if "private fun refreshLatestMinecraftVersion()" not in source:
        anchor = "    private fun rendererPage() {"
        if anchor not in source:
            raise SystemExit("[step328] rendererPage anchor not found")
        source = source.replace(anchor, refresh + anchor, 1)

    # Refresh when the visible game/version pages are rebuilt. Do not add duplicate calls.
    for signature in ("    private fun gamePage() {", "    private fun libraryPage(page: String) {"):
        pos = source.find(signature)
        if pos < 0:
            continue
        body_start = source.find("{", pos)
        next_decl = source.find("\n    private fun ", body_start + 1)
        body = source[body_start: next_decl if next_decl >= 0 else len(source)]
        if "refreshLatestMinecraftVersion()" not in body:
            newline = body.find("\n")
            insert_at = body_start + (newline + 1 if newline >= 0 else 1)
            source = source[:insert_at] + "        refreshLatestMinecraftVersion()\n" + source[insert_at:]

    # Replace common hard-coded version list with a cached-latest-first helper.
    helper = '''    private fun selectLatestMinecraftVersion() {
        val latest = MinecraftLatestVersionManager.getCached(this)?.trim().orEmpty()
        if (latest.isNotEmpty()) {
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("selected_minecraft_version", latest)
                .apply()
            showPage("Game")
        } else {
            refreshLatestMinecraftVersion()
            android.widget.Toast.makeText(this, "Checking Mojang for the latest release…", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private fun minecraftVersionChoices(): List<String> {
        val cached = MinecraftLatestVersionManager.getCached(this)
        val known = listOf("26.3", "26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4", "1.18.2", "1.16.5")
        return (listOfNotNull(cached) + known).distinct()
    }

'''
    if "private fun minecraftVersionChoices(): List<String>" not in source:
        anchor = "    private fun rendererPage() {"
        if anchor not in source:
            raise SystemExit("[step328] rendererPage anchor not found for version helper")
        source = source.replace(anchor, helper + anchor, 1)

    source = source.replace(
        'val versions = listOf("1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4", "1.18.2", "1.16.5")',
        'val versions = minecraftVersionChoices()',
        1,
    )
    source = source.replace(
        'else -> listOf("26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9")',
        'else -> minecraftVersionChoices()',
        1,
    )
    ui.write_text(source, encoding="utf-8")
    print("[step328] selected Minecraft version now prefers cached Mojang latest")
    print("[step328] Game/library pages refresh latest metadata without blocking UI")
    print("[step328] version lists prepend the cached latest release and de-duplicate entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
