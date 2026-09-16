#!/usr/bin/env python3
"""Step 218: make Minecraft-version -> Java-runtime resolution deterministic and self-healing."""
from pathlib import Path
import re
import sys

HELPERS = '''    private fun recommendedJavaForVersion(version: String): Int {
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

JAVA_PAGE = '''    private fun javaPage() {
        pageArea.addView(section("Java", "Automatic runtime selection with per-version override"))
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val selected = prefs.getString("selected_java_runtime", "auto") ?: "auto"
        System.setProperty("droid.launcher.java.runtime", selected)
        val autoCard = cardView(12)
        autoCard.addView(label("Automatic", 16f, true))
        autoCard.addView(label("Chooses Java from the Minecraft version unless you select an override.", 12f, false))
        val autoLine = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        autoLine.addView(label("Current: ${if (selected == "auto") "AUTO" else selected}", 13f), LinearLayout.LayoutParams(0, dp(44), 1f))
        val autoButton = button("Use Auto", selected == "auto")
        autoButton.setOnClickListener { saveJavaOverride("auto"); showPage("Java") }
        autoLine.addView(autoButton)
        autoCard.addView(autoLine)
        pageArea.addView(autoCard)
        val examples = listOf("1.16.5", "1.18.2", "1.20.4", "1.20.6", "1.21.1", "1.21.11", "25.1")
        examples.forEach { version ->
            val recommended = resolveJavaForVersion(version)
            val c = cardView(12)
            c.addView(label("Minecraft $version", 15f, true))
            c.addView(label("Recommended: Java $recommended", 12f, false))
            val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            line.addView(label("Override runtime", 12f), LinearLayout.LayoutParams(0, dp(42), 1f))
            listOf("Auto", "Internal-8", "Internal-17", "Internal-21", "Internal-25").forEach { option ->
                val b = button(option, (selected == "auto" && option == "Auto") || selected == option)
                b.setOnClickListener { saveJavaOverride(if (option == "Auto") "auto" else option); showPage("Java") }
                line.addView(b, LinearLayout.LayoutParams(dp(82), dp(42)))
            }
            c.addView(line)
            pageArea.addView(c)
        }
    }

'''


def replace_method(source: str, signature: str, replacement: str, next_signatures: list[str]) -> str:
    start = source.find(signature)
    if start < 0:
        return source
    candidates = [source.find(sig, start + len(signature)) for sig in next_signatures]
    candidates = [i for i in candidates if i >= 0]
    if not candidates:
        return source
    end = min(candidates)
    return source[:start] + replacement + source[end:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step218] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Remove duplicate copies of our helper methods before inserting the canonical one.
    for signature in [
        r'    private fun recommendedJavaForVersion\(version: String\): Int \{[\s\S]*?^    \}\n\n',
        r'    private fun storedJavaOverride\(\): Int\? \{[\s\S]*?^    \}\n\n',
        r'    private fun resolveJavaForVersion\(version: String\): Int =[^\n]*\n',
        r'    private fun saveJavaOverride\(value: String\) \{[\s\S]*?^    \}\n\n',
        r'    private fun getResolvedJavaForLaunch\(version: String\): Int =[^\n]*\n',
    ]:
        s = re.sub(signature, '', s, count=1, flags=re.M)

    # Replace Java page when possible. Prefer the explicit controls boundary, then any
    # top-level private member; this handles generated UI variants from later steps.
    start = s.find('    private fun javaPage() {')
    if start >= 0:
        end = s.find('    private fun controlsPage()', start)
        if end < 0:
            m = re.search(r'(?m)^    private fun [A-Za-z0-9_]+\([^\n]*\) \{', s[start + 1:])
            end = start + 1 + m.start() if m else -1
        if end >= 0:
            s = s[:start] + JAVA_PAGE + s[end:]
        else:
            raise SystemExit('[step218] unable to locate end of javaPage for safe replacement')
    else:
        # The Java page was deleted by a later generator. Add it before rendererPage;
        # the following steps only require the helper and method contracts to exist.
        anchor = s.find('    private fun rendererPage() {')
        if anchor < 0:
            anchor = s.find('    private fun gamePage() {')
        if anchor < 0:
            raise SystemExit('[step218] no stable UI insertion anchor found')
        s = s[:anchor] + JAVA_PAGE + s[anchor:]

    # Put one canonical helper block immediately before rendererPage.
    s = re.sub(r'\n{3,}', '\n\n', s)
    anchor = s.find('    private fun rendererPage() {')
    if anchor < 0:
        raise SystemExit('[step218] rendererPage anchor not found')
    s = s[:anchor] + HELPERS + s[anchor:]

    required = [
        'private fun recommendedJavaForVersion(version: String): Int',
        'private fun storedJavaOverride(): Int?',
        'private fun resolveJavaForVersion(version: String): Int',
        'private fun saveJavaOverride(value: String)',
        'private fun getResolvedJavaForLaunch(version: String): Int',
        'private fun javaPage() {',
        'System.setProperty("droid.launcher.java.runtime", value)',
    ]
    for needle in required:
        if needle not in s:
            raise SystemExit(f'[step218] missing contract after repair: {needle}')

    ui.write_text(s, encoding='utf-8')
    print('[step218] Java resolver/helper contract restored deterministically')
    print('[step218] Java page replacement tolerates late UI rewrites')
    print('[step218] explicit Java 8/16/17/21/25 overrides persisted')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
