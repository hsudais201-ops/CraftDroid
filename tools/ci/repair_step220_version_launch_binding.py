#!/usr/bin/env python3
"""Step 220: bind the selected Minecraft version/profile to the real launch intent."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step220] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def canonical_java_helpers(s: str) -> str:
    """Restore resolver helpers after any page replacement that may have swallowed them."""
    helpers = '''    private fun recommendedJavaForVersion(version: String): Int {
        val nums = version.split('.').mapNotNull { it.toIntOrNull() }
        val major = nums.getOrNull(0) ?: return 17
        val minor = nums.getOrNull(1) ?: 0
        val patch = nums.getOrNull(2) ?: 0
        return when {
            major == 1 && minor <= 16 -> 8
            major == 1 && minor <= 19 -> 17
            major == 1 && minor == 20 && patch < 5 -> 17
            major == 1 && (minor > 20 || (minor == 20 && patch >= 5)) -> 21
            major >= 25 -> 25
            else -> 21
        }
    }

    private fun storedJavaOverride(): Int? {
        val raw = getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_java_runtime", "auto") ?: "auto"
        return raw.removePrefix("Internal-").toIntOrNull()
    }

    private fun resolveJavaForVersion(version: String): Int =
        storedJavaOverride() ?: recommendedJavaForVersion(version)

    private fun saveJavaOverride(value: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("selected_java_runtime", value)
            .apply()
        System.setProperty("droid.launcher.java.runtime", value)
    }

    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

'''
    # Remove duplicate helper declarations without touching unrelated methods.
    import re
    s = re.sub(r'(?ms)^    private fun recommendedJavaForVersion\(version: String\): Int \{.*?^    \}\n\n', '', s, count=1)
    s = re.sub(r'(?ms)^    private fun storedJavaOverride\(\): Int\? \{.*?^    \}\n\n', '', s, count=1)
    s = re.sub(r'(?m)^    private fun resolveJavaForVersion\(version: String\): Int =[^\n]*\n', '', s, count=1)
    s = re.sub(r'(?ms)^    private fun saveJavaOverride\(value: String\) \{.*?^    \}\n\n', '', s, count=1)
    s = re.sub(r'(?m)^    private fun getResolvedJavaForLaunch\(version: String\): Int =[^\n]*\n', '', s, count=1)
    anchor = s.find('    private fun rendererPage() {')
    if anchor < 0:
        raise SystemExit('[step220] rendererPage anchor missing while restoring Java helpers')
    return s[:anchor] + helpers + s[anchor:]


def patch_java_resolver(s: str) -> str:
    # The canonical helper is restored after gamePage replacement, so this patch is
    # intentionally a no-op. Keeping the helper body in exactly one place prevents
    # Step 220 from deleting Step 218's resolver contract.
    return s


def patch_game_page(s: str) -> str:
    marker = '    private fun gamePage() {'
    start = s.find(marker)
    end = s.find('\n    private fun rendererPage()', start)
    if start < 0 or end < 0:
        raise SystemExit("[step220] gamePage anchors not found")
    new_page = '''    private fun gamePage() {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val selectedVersion = prefs.getString("selected_minecraft_version", "1.21.11") ?: "1.21.11"
        val selectedProfile = prefs.getString("selected_minecraft_profile", "Default") ?: "Default"
        val effectiveJava = getResolvedJavaForLaunch(selectedVersion)

        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val left = cardView(18)
        left.addView(label("Minecraft profile", 19f, true))
        left.addView(label("Version: $selectedVersion", 13f, true))
        left.addView(label("Profile: $selectedProfile", 13f, false))
        left.addView(label("Java: $effectiveJava", 13f, false))
        val library = button("▣  Choose Version")
        library.setOnClickListener { showPage("Search by ID") }
        left.addView(library, LinearLayout.LayoutParams(-1, dp(46)))
        val profileButton = button("◆  Profile: $selectedProfile")
        profileButton.setOnClickListener {
            val next = if (selectedProfile == "Default") "Performance" else "Default"
            prefs.edit().putString("selected_minecraft_profile", next).apply()
            showPage("Game")
        }
        left.addView(profileButton, LinearLayout.LayoutParams(-1, dp(46)))
        val add = button("+  Add Account")
        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))
        row.addView(left, LinearLayout.LayoutParams(0, -1, 1f))

        val right = cardView(18)
        right.gravity = Gravity.CENTER
        right.addView(label("Minecraft Java Edition", 20f, true))
        right.addView(label("Ready: $selectedVersion  ·  $selectedProfile  ·  Java $effectiveJava", 13f))
        val launch = button("Launch", true)
        launch.setOnClickListener { launchExistingActivityWithServer() }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(52)))
        row.addView(right, LinearLayout.LayoutParams(dp(360), -1))
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360)))
    }
'''
    return s[:start] + new_page + s[end:]


def patch_library_page(s: str) -> str:
    old = '''            line.addView(button(if (page == "Saves") "Import" else "Install"))
            c.addView(line)
            pageArea.addView(c)
'''
    new = '''            val action = button(if (page == "Saves") "Import" else if (page == "Search by ID") "Select" else "Install")
            if (page == "Search by ID") {
                action.setOnClickListener {
                    getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                        .putString("selected_minecraft_version", item)
                        .apply()
                    android.widget.Toast.makeText(this, "Selected Minecraft $item", android.widget.Toast.LENGTH_SHORT).show()
                    showPage("Game")
                }
            }
            line.addView(action)
            c.addView(line)
            pageArea.addView(c)
'''
    if old not in s:
        raise SystemExit("[step220] library version action anchor not found")
    return s.replace(old, new, 1)


def find_method_end(s: str, start: int) -> int:
    next_member = s.find('\n    private fun ', start + 1)
    companion = s.find('\n    companion object', start + 1)
    candidates = [x for x in (next_member, companion) if x >= 0]
    if not candidates: raise SystemExit('[step220] end of selected-server launch method not found')
    return min(candidates)


def patch_launch_method(s: str) -> str:
    marker = '    private fun launchExistingActivityWithServer() {'
    start = s.find(marker)
    if start < 0: raise SystemExit("[step220] selected-server launch method not found")
    end = find_method_end(s, start)
    block = s[start:end]
    if 'selected_minecraft_version' not in block:
        needle = '        val endpoint = "${saved.first}:${saved.second}"\n'
        if needle not in block: raise SystemExit("[step220] launch endpoint anchor not found")
        block = block.replace(needle, needle + '''        val launchPrefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val selectedVersion = launchPrefs.getString("selected_minecraft_version", "1.21.11") ?: "1.21.11"
        val selectedProfile = launchPrefs.getString("selected_minecraft_profile", "Default") ?: "Default"
        val resolvedJava = getResolvedJavaForLaunch(selectedVersion)
''', 1)
    extras_anchor = '            intent.putExtra("minecraft_server", endpoint)\n'
    if 'intent.putExtra("minecraft_version", selectedVersion)' not in block:
        if extras_anchor not in block: raise SystemExit("[step220] launch server extra anchor not found")
        block = block.replace(extras_anchor, extras_anchor + '''            intent.putExtra("minecraft_version", selectedVersion)
            intent.putExtra("minecraft_profile", selectedProfile)
            intent.putExtra("minecraft_java", resolvedJava)
            intent.putExtra("java_runtime", launchPrefs.getString("selected_java_runtime", "auto") ?: "auto")
''', 1)
    return s[:start] + block + s[end:]


def patch_launch_log(s: str) -> str:
    needle = '            android.widget.Toast.makeText(this, "Launching Droid Launcher for $endpoint…", android.widget.Toast.LENGTH_SHORT).show()\n'
    if needle not in s or 'Version $selectedVersion' in s: return s
    return s.replace(needle, needle + '            android.widget.Toast.makeText(this, "Version $selectedVersion  ·  Profile $selectedProfile  ·  Java $resolvedJava", android.widget.Toast.LENGTH_SHORT).show()\n', 1)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    ui = find_one(src, "DroidLauncherUiActivity.kt")
    s = ui.read_text(encoding="utf-8")
    s = patch_java_resolver(s)
    s = patch_game_page(s)
    # IMPORTANT: patch_game_page replaces everything up to rendererPage, which can
    # swallow Step 218 helpers. Restore them *after* that replacement.
    s = canonical_java_helpers(s)
    s = patch_library_page(s)
    s = patch_launch_method(s)
    s = patch_launch_log(s)
    ui.write_text(s, encoding="utf-8")

    checks = [
        'selected_minecraft_version',
        'selected_minecraft_profile',
        'intent.putExtra("minecraft_version", selectedVersion)',
        'intent.putExtra("minecraft_profile", selectedProfile)',
        'intent.putExtra("minecraft_java", resolvedJava)',
        'private fun recommendedJavaForVersion(version: String): Int',
        'private fun resolveJavaForVersion(version: String): Int',
        'private fun getResolvedJavaForLaunch(version: String): Int',
    ]
    for needle in checks:
        if needle not in s: raise SystemExit(f"[step220] missing contract: {needle}")
    print("[step220] selected Minecraft version persisted from version library")
    print("[step220] selected profile persisted and shown on Game page")
    print("[step220] version/profile/effective Java added to real launch intent")
    print("[step220] canonical Java resolver restored after gamePage replacement")
    return 0

if __name__ == "__main__": raise SystemExit(main())
