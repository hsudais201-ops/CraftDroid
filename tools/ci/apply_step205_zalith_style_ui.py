#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ACTIVITY = r'''package com.example.launcher

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

class DroidLauncherUiActivity : Activity() {
    private val pageArea by lazy { LinearLayout(this) }
    private val title by lazy { TextView(this) }
    private var currentPage = "Game"

    private val bg = Color.rgb(246, 248, 251)
    private val card = Color.WHITE
    private val accent = Color.rgb(35, 82, 122)
    private val text = Color.rgb(31, 37, 44)
    private val muted = Color.rgb(92, 100, 110)

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        buildUi()
        showPage("Game")
    }

    private fun dp(v: Int) = (v * resources.displayMetrics.density).toInt()

    private fun label(value: String, size: Float = 14f, bold: Boolean = false): TextView = TextView(this).apply {
        text = value
        textSize = size
        setTextColor(text)
        typeface = Typeface.create("sans", if (bold) Typeface.BOLD else Typeface.NORMAL)
        setPadding(dp(10), dp(6), dp(10), dp(6))
    }

    private fun button(value: String, filled: Boolean = false): Button = Button(this).apply {
        text = value
        isAllCaps = false
        textSize = 13f
        setTextColor(if (filled) Color.WHITE else text)
        setPadding(dp(8), 0, dp(8), 0)
        if (filled) setBackgroundColor(accent) else setBackgroundColor(Color.TRANSPARENT)
    }

    private fun cardView(padding: Int = 14): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(padding), dp(padding), dp(padding), dp(padding))
        setBackgroundColor(card)
        elevation = dp(2).toFloat()
        layoutParams = LinearLayout.LayoutParams(-1, -2).apply { setMargins(dp(5), dp(5), dp(5), dp(5)) }
    }

    private fun buildUi() {
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setBackgroundColor(bg) }

        val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(10), dp(4), dp(8), dp(4)) }
        title.text = "Droid Launcher"
        title.textSize = 18f
        title.setTextColor(text)
        title.typeface = Typeface.DEFAULT_BOLD
        top.addView(title, LinearLayout.LayoutParams(0, dp(48), 1f))
        listOf("▣", "♟", "⇩", "⚙").forEach { icon ->
            val b = button(icon)
            top.addView(b, LinearLayout.LayoutParams(dp(48), dp(48)))
            if (icon == "⚙") b.setOnClickListener { showPage("Renderer") }
        }
        root.addView(top, LinearLayout.LayoutParams(-1, dp(54)))

        val body = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val rail = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.TOP; setPadding(dp(4), dp(4), dp(4), dp(4)) }
        val nav = listOf(
            "⌂" to "Game", "◇" to "Modpack", "☆" to "Mod", "▣" to "Resource Pack",
            "◉" to "Saves", "♢" to "Shader Pack", "⌕" to "Search by ID",
            "⚙" to "Renderer", "◌" to "Java", "▤" to "Controls", "ⓘ" to "About"
        )
        nav.forEach { (icon, page) ->
            val b = button("$icon\n$page")
            b.textSize = 10f
            b.gravity = Gravity.CENTER
            b.setOnClickListener { showPage(page) }
            rail.addView(b, LinearLayout.LayoutParams(dp(92), dp(62)))
        }
        body.addView(rail, LinearLayout.LayoutParams(dp(104), -1))
        val scroll = ScrollView(this)
        pageArea.orientation = LinearLayout.VERTICAL
        pageArea.setPadding(dp(6), dp(2), dp(12), dp(12))
        scroll.addView(pageArea)
        body.addView(scroll, LinearLayout.LayoutParams(0, -1, 1f))
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }

    private fun showPage(page: String) {
        currentPage = page
        title.text = "Droid Launcher  ·  $page"
        pageArea.removeAllViews()
        when (page) {
            "Game" -> gamePage()
            "Renderer" -> rendererPage()
            "Java" -> javaPage()
            "Controls" -> controlsPage()
            "Modpack", "Mod", "Resource Pack", "Saves", "Shader Pack", "Search by ID" -> libraryPage(page)
            else -> aboutPage()
        }
    }

    private fun gamePage() {
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val left = cardView(18)
        left.addView(label("No account selected", 19f, true))
        left.addView(label("Add an account to unlock Minecraft profiles and launching.", 13f))
        val add = button("+  Add Account")
        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))
        row.addView(left, LinearLayout.LayoutParams(0, -1, 1f))

        val right = cardView(18)
        right.gravity = Gravity.CENTER
        right.addView(label("Minecraft Java Edition", 20f, true))
        right.addView(label("Select a version, runtime, and profile.", 13f))
        val launch = button("Launch", true)
        launch.setOnClickListener { launchExistingActivity() }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(52)))
        row.addView(right, LinearLayout.LayoutParams(dp(330), -1))
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360)))
    }

    private fun rendererPage() {
        pageArea.addView(section("Settings · Renderer", "Mobile-first renderer and display controls"))
        setting("Global Renderer", "Krypton Wrapper", "Dynamic translation layer for broad device compatibility")
        setting("Vulkan Driver", "Turnip", "Select the preferred Vulkan implementation where available")
        setting("Graphics API", "Automatic", "Use the first supported graphics backend at launch")
        setting("Resolution Rule", "Percentage", "Choose how the game window resolution is calculated")
        setting("Resolution Scale", "100%", "Lower values improve performance; higher values improve sharpness")
        setting("Game Fullscreen", "Enabled", "Ignore safe areas such as notches and punch-holes")
    }

    private fun javaPage() {
        pageArea.addView(section("Java", "Runtime environments used by Minecraft versions"))
        listOf("Internal-8" to "Java 8 · legacy Minecraft 1.16 and below", "Internal-17" to "Java 17 · Minecraft 1.17+", "Internal-21" to "Java 21 · Minecraft 1.20.5+", "Internal-25" to "Java 25 · Minecraft 25.1+").forEach {
            val c = cardView(12)
            c.addView(label(it.first, 16f, true))
            c.addView(label(it.second, 13f, false))
            c.addView(button("Select  ·  Download"))
            pageArea.addView(c)
        }
    }

    private fun controlsPage() {
        pageArea.addView(section("Controls", "Fully customizable touch layout"))
        setting("Movement", "Joystick + Forward / Back / Left / Right", "Drag, resize, change opacity and position")
        setting("Actions", "Jump · Sneak · Sprint · Attack · Use · Drop · Inventory · Chat · Pause", "Each control is independently editable")
        setting("Camera", "Mouse / Camera Area", "Dedicated look surface for Java mouse input")
        val c = cardView()
        val row = LinearLayout(this)
        row.addView(button("RESET"), LinearLayout.LayoutParams(0, dp(48), 1f))
        row.addView(button("+ ADD CONTROL", true), LinearLayout.LayoutParams(0, dp(48), 1f))
        row.addView(button("SAVE", true), LinearLayout.LayoutParams(0, dp(48), 1f))
        c.addView(row)
        pageArea.addView(c)
    }

    private fun libraryPage(page: String) {
        pageArea.addView(section("Download · $page", "Modern launcher-style library browser"))
        val items = when (page) {
            "Search by ID" -> listOf("1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4")
            "Saves" -> listOf("Survival World", "Creative Test", "Skyblock Backup")
            else -> listOf("26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9")
        }
        items.forEachIndexed { i, item ->
            val c = cardView(12)
            val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            line.addView(label("▣", 22f), LinearLayout.LayoutParams(dp(34), dp(48)))
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            info.addView(label(item, 16f, true))
            info.addView(label(if (page == "Game" || page == "Search by ID") "Release  ·  Android ready" else "Managed item  ·  Profile storage", 12f))
            line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
            line.addView(button(if (page == "Saves") "Import" else "Install"))
            c.addView(line)
            pageArea.addView(c)
        }
    }

    private fun aboutPage() {
        pageArea.addView(section("Droid Launcher", "A landscape-first Minecraft: Java Edition launcher interface"))
        setting("Build", "Step 205 UI", "Zalith-style navigation, cards, download lists and settings shell")
        setting("Brand", "Droid Launcher", "Repository remains CraftDroid")
        setting("Runtime", "Cloud-built APK", "UI layer is applied during the consolidated CI build")
    }

    private fun section(head: String, sub: String): TextView = label("$head\n$sub", 16f, true).apply {
        setPadding(dp(12), dp(10), dp(12), dp(10))
    }

    private fun setting(name: String, value: String, description: String) {
        val c = cardView(12)
        c.addView(label(name, 15f, true))
        c.addView(label(description, 12f, false))
        val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        line.addView(label("Selected: $value", 13f), LinearLayout.LayoutParams(0, dp(44), 1f))
        line.addView(button("⌄"))
        c.addView(line)
        pageArea.addView(c)
    }

    private fun launchExistingActivity() {
        val component = EXISTING_LAUNCHER_COMPONENT
        if (component.isBlank()) return
        val parts = component.split('/', limit = 2)
        if (parts.size == 2) {
            try {
                val i = Intent().setClassName(packageName, parts[1].removePrefix("."))
                startActivity(i)
            } catch (_: Exception) {
            }
        }
    }

    companion object {
        private const val EXISTING_LAUNCHER_COMPONENT = "__EXISTING_LAUNCHER_COMPONENT__"
    }
}
'''


def find_manifest(root: Path) -> Path:
    matches = list(root.glob("**/src/main/AndroidManifest.xml"))
    if not matches:
        raise SystemExit(f"[step205] no AndroidManifest.xml under {root}")
    return matches[0]


def get_launcher_component(text: str) -> str:
    activity_pattern = r'<(?:activity|activity-alias)\b[\s\S]*?</(?:activity|activity-alias)>'
    for m in re.finditer(activity_pattern, text):
        block = m.group(0)
        if "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            am = re.search(r'android:name="([^"]+)"', block)
            if am:
                name = am.group(1)
                if name.startswith("."):
                    pkg = re.search(r'<manifest[^>]*android:package="([^"]+)"', text)
                    if pkg:
                        name = pkg.group(1) + name
                return name
    for m in re.finditer(r'<(?:activity|activity-alias)\b[^>]*?/\s*>', text):
        block = m.group(0)
        if "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            am = re.search(r'android:name="([^"]+)"', block)
            if am:
                name = am.group(1)
                if name.startswith("."):
                    pkg = re.search(r'<manifest[^>]*android:package="([^"]+)"', text)
                    if pkg:
                        name = pkg.group(1) + name
                return name
    return ""


def add_activity(text: str) -> str:
    if "com.example.launcher.DroidLauncherUiActivity" in text:
        return text
    activity = '''\n        <activity\n            android:name="com.example.launcher.DroidLauncherUiActivity"\n            android:screenOrientation="landscape"\n            android:exported="true"\n            android:label="Droid Launcher">\n            <intent-filter>\n                <action android:name="android.intent.action.MAIN" />\n                <category android:name="android.intent.category.LAUNCHER" />\n            </intent-filter>\n        </activity>\n'''
    marker = "</application>"
    return text.replace(marker, activity + "    " + marker, 1)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    manifest = find_manifest(root)
    text = manifest.read_text(encoding="utf-8")
    existing = get_launcher_component(text)
    activity = ACTIVITY.replace("__EXISTING_LAUNCHER_COMPONENT__", existing)
    src = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(activity, encoding="utf-8")
    manifest.write_text(add_activity(text), encoding="utf-8")
    print(f"[step205] UI installed: {src}")
    print(f"[step205] existing launcher preserved: {existing or 'none detected'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
