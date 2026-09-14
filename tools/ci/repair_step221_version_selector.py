#!/usr/bin/env python3
"""Step 221/239: install a persistent Minecraft version selector for Droid Launcher."""
from pathlib import Path
import re
import sys


def remove_duplicate_functions(source: str, signature: str) -> tuple[str, int]:
    """Keep the first top-level private function with a signature and remove later duplicates."""
    positions = [m.start() for m in re.finditer(re.escape(signature), source)]
    if len(positions) <= 1:
        return source, 0

    def block_end(s: str, start: int) -> int:
        brace = s.find('{', start)
        if brace < 0:
            raise SystemExit(f'[step239] function body opening brace not found: {signature}')
        depth = 0
        in_string = False
        escaped = False
        for i in range(brace, len(s)):
            ch = s[i]
            if in_string:
                if escaped:
                    escaped = False
                elif ch == '\\':
                    escaped = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    j = i + 1
                    while j < len(s) and s[j] in '\r\n':
                        j += 1
                    return j
        raise SystemExit(f'[step239] unterminated function body: {signature}')

    removed = 0
    for start in reversed(positions[1:]):
        end = block_end(source, start)
        source = source[:start] + source[end:]
        removed += 1
    return source, removed


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step221] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    helper = '''    private fun selectedMinecraftVersion(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_version", "1.21.11") ?: "1.21.11"

    private fun saveMinecraftVersion(version: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .edit().putString("selected_minecraft_version", version).apply()
    }

    private fun selectedMinecraftProfile(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_profile", "Default") ?: "Default"

    private fun saveMinecraftProfile(profile: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .edit().putString("selected_minecraft_profile", profile).apply()
    }

    private fun launchSelectedMinecraft() {
        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
        val java = getResolvedJavaForLaunch(version)
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("last_launch_version", version)
            .putString("last_launch_profile", profile)
            .putInt("last_launch_java", java)
            .apply()
        launchExistingActivityWithServer()
    }

'''
    if 'private fun selectedMinecraftVersion(): String' not in s:
        anchor = '    private fun rendererPage() {'
        if anchor not in s:
            raise SystemExit('[step221] rendererPage anchor not found')
        s = s.replace(anchor, helper + anchor, 1)

    start = s.find('    private fun gamePage() {')
    end = s.find('    private fun rendererPage() {', start)
    if start < 0 or end < 0:
        raise SystemExit('[step221] gamePage anchors not found')

    new_game = '''    private fun gamePage() {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
        val java = getResolvedJavaForLaunch(version)
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }

        val left = cardView(18)
        left.addView(label("Minecraft profile", 17f, true))
        left.addView(label("$profile", 20f, true))
        left.addView(label("Version  ·  $version", 13f, false))
        left.addView(label("Java  ·  $java", 13f, false))
        val versionButton = button("Choose Version")
        versionButton.setOnClickListener { showPage("Search by ID") }
        left.addView(versionButton, LinearLayout.LayoutParams(-1, dp(46)))
        row.addView(left, LinearLayout.LayoutParams(0, -1, 1f))

        val right = cardView(18)
        right.gravity = Gravity.CENTER
        right.addView(label("Minecraft Java Edition", 20f, true))
        right.addView(label("$version  ·  $profile", 14f, true))
        right.addView(label("Java $java", 13f, false))
        val launch = button("▶  PLAY", true)
        launch.setOnClickListener { launchSelectedMinecraft() }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(56)))
        row.addView(right, LinearLayout.LayoutParams(dp(330), -1))
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360)))
    }

'''
    s = s[:start] + new_game + s[end:]

    start = s.find('    private fun libraryPage(page: String) {')
    end = s.find('    private fun aboutPage() {', start)
    if start < 0 or end < 0:
        raise SystemExit('[step221] libraryPage anchors not found')

    new_library = '''    private fun libraryPage(page: String) {
        if (page != "Search by ID") {
            pageArea.addView(section("Download · $page", "Modern launcher-style library browser"))
            val items = when (page) {
                "Saves" -> listOf("Survival World", "Creative Test", "Skyblock Backup")
                else -> listOf("26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9")
            }
            items.forEach { item ->
                val c = cardView(12)
                val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
                line.addView(label("▣", 22f), LinearLayout.LayoutParams(dp(34), dp(48)))
                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                info.addView(label(item, 16f, true))
                info.addView(label(if (page == "Saves") "Managed save" else "Managed item · Profile storage", 12f))
                line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
                line.addView(button(if (page == "Saves") "Import" else "Install"))
                c.addView(line)
                pageArea.addView(c)
            }
            return
        }

        pageArea.addView(section("Minecraft Versions", "Select a version to use with Play"))
        val versions = listOf("1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4", "1.18.2", "1.16.5")
        val selected = selectedMinecraftVersion()
        versions.forEach { item ->
            val c = cardView(12)
            val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            line.addView(label(if (item == selected) "✓" else "○", 24f), LinearLayout.LayoutParams(dp(38), dp(52)))
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            info.addView(label(item, 17f, true))
            val java = getResolvedJavaForLaunch(item)
            info.addView(label("Recommended Java $java  ·  ${if (item == "1.21.11") "Installed" else "Available"}", 12f))
            line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
            val choose = button(if (item == selected) "Selected" else "Select", item == selected)
            choose.setOnClickListener {
                saveMinecraftVersion(item)
                showPage("Game")
            }
            line.addView(choose, LinearLayout.LayoutParams(dp(110), dp(46)))
            c.addView(line)
            pageArea.addView(c)
        }

        val profile = cardView(12)
        profile.addView(label("Profile", 16f, true))
        profile.addView(label("${selectedMinecraftProfile()}  ·  persistent launch profile", 12f, false))
        val profileLine = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        listOf("Default", "Survival", "PvP", "Modded").forEach { name ->
            val b = button(name, name == selectedMinecraftProfile())
            b.setOnClickListener { saveMinecraftProfile(name); showPage("Search by ID") }
            profileLine.addView(b, LinearLayout.LayoutParams(0, dp(44), 1f))
        }
        profile.addView(profileLine)
        pageArea.addView(profile)
    }

'''
    s = s[:start] + new_library + s[end:]

    # Canonicalize helpers after all earlier/later generators have touched the file.
    removed_total = 0
    for signature in (
        '    private fun selectedMinecraftVersion(): String',
        '    private fun saveMinecraftVersion(version: String)',
        '    private fun selectedMinecraftProfile(): String',
        '    private fun saveMinecraftProfile(profile: String)',
        '    private fun launchSelectedMinecraft()',
    ):
        s, removed = remove_duplicate_functions(s, signature)
        removed_total += removed

    ui.write_text(s, encoding="utf-8")
    print('[step221] persistent Minecraft version/profile selector installed')
    print('[step221] Game screen now reflects selected version and resolved Java')
    print('[step221] Play uses selected version/profile state')
    print(f'[step239] duplicate version/profile/launch helpers removed: {removed_total}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
