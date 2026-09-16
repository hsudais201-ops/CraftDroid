#!/usr/bin/env python3
"""Step 218: wire Minecraft version -> Java runtime selection into the generated UI."""
from pathlib import Path
import sys

def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step218] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    helper = '''    private fun recommendedJavaForVersion(version: String): Int {
        val parts = version.split('.').mapNotNull { it.toIntOrNull() }
        val major = parts.getOrNull(0) ?: return 17
        val minor = parts.getOrNull(1) ?: 0
        val patch = parts.getOrNull(2) ?: 0
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
        val value = getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("selected_java_runtime", "auto") ?: "auto"
        return value.removePrefix("Internal-").toIntOrNull()
    }

    private fun resolveJavaForVersion(version: String): Int = storedJavaOverride() ?: recommendedJavaForVersion(version)

    private fun saveJavaOverride(value: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit().putString("selected_java_runtime", value).apply()
        System.setProperty("droid.launcher.java.runtime", value)
    }

    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

'''
    # Always restore the helper block if any later generator removed it.
    for sig in ('    private fun recommendedJavaForVersion(version: String): Int {', '    private fun storedJavaOverride(): Int?', '    private fun resolveJavaForVersion(version: String): Int =', '    private fun saveJavaOverride(value: String) {', '    private fun getResolvedJavaForLaunch(version: String): Int ='):
        if sig not in s:
            anchor = s.find('    private fun rendererPage() {')
            if anchor < 0: raise SystemExit('[step218] rendererPage anchor not found')
            s = s[:anchor] + helper + s[anchor:]
            break

    # Replace only the javaPage body; helpers remain immediately before rendererPage.
    start = s.find('    private fun javaPage() {')
    end = s.find('\n    private fun controlsPage()', start)
    if start < 0 or end < 0: raise SystemExit('[step218] javaPage block not found')
    new_page = '''    private fun javaPage() {
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
            c.addView(line); pageArea.addView(c)
        }
    }
'''
    s = s[:start] + new_page + s[end:]
    ui.write_text(s, encoding="utf-8")
    print('[step218] Java resolver/helper contract restored and persisted')
    return 0

if __name__ == '__main__': raise SystemExit(main())
