#!/usr/bin/env python3
"""Step 218: wire Minecraft version -> Java runtime selection into the UI build."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step218] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    anchor = '    private fun javaPage() {'
    if 'private fun recommendedJavaForVersion(version: String): Int' not in s:
        helper = '''    private fun recommendedJavaForVersion(version: String): Int {
        val nums = version.split('.').mapNotNull { it.toIntOrNull() }
        val major = nums.getOrNull(0) ?: return 17
        val minor = nums.getOrNull(1) ?: 0
        return when {
            major <= 1 && minor <= 16 -> 8
            major == 1 && minor <= 20 -> 17
            major == 1 && minor >= 20 -> 21
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
    }

'''
        if anchor not in s:
            raise SystemExit('[step218] javaPage anchor not found')
        s = s.replace(anchor, helper + anchor, 1)

    # Upgrade the Java page so AUTO is visible and each runtime can be selected explicitly.
    start = s.find('    private fun javaPage() {')
    end = s.find('    private fun controlsPage()', start)
    if start < 0 or end < 0:
        raise SystemExit('[step218] javaPage block not found')
    new_page = '''    private fun javaPage() {
        pageArea.addView(section("Java", "Automatic runtime selection with per-version override"))
        val selected = getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("selected_java_runtime", "auto") ?: "auto"
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
    s = s[:start] + new_page + s[end:]

    # Add launch diagnostics helper so later launch steps can call a resolved Java major.
    anchor2 = '    private fun rendererPage() {'
    if 'private fun getResolvedJavaForLaunch(version: String): Int' not in s:
        helper2 = '''    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

'''
        if anchor2 in s:
            s = s.replace(anchor2, helper2 + anchor2, 1)

    ui.write_text(s, encoding="utf-8")
    print('[step218] automatic Minecraft-version Java resolver installed')
    print('[step218] explicit Java 8/17/21/25 override support installed')
    print('[step218] persisted runtime override installed')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
