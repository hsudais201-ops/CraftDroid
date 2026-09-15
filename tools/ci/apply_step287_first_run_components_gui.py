#!/usr/bin/env python3
"""Step 287: add the isolated first-run bundled-components extraction gate.

The gate is deliberately outside the normal launcher navigation: no Home,
Accounts, Downloads or Settings controls are rendered until extraction has
completed successfully. It persists completion only after every required
component has been copied and verified from the APK assets.
"""
from pathlib import Path
import sys


def find_ui(root: Path) -> Path:
    matches = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(matches) != 1:
        raise SystemExit(f"[step287] expected one DroidLauncherUiActivity.kt, found {len(matches)}")
    return matches[0]


def replace_method(source: str, signature: str, replacement: str) -> str:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step287] missing method: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step287] missing opening brace: {signature}")
    depth = 0
    quoted = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quoted:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quoted = False
            continue
        if ch == '"':
            quoted = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[:start] + replacement + source[i + 1:]
    raise SystemExit(f"[step287] unterminated method: {signature}")


HELPERS = r'''    private data class BootstrapComponent(val name: String, val description: String)

    private val bootstrapComponents = listOf(
        BootstrapComponent("authlib-injector", "Modifies authlib at runtime to enable external logins."),
        BootstrapComponent("caciocavallo", "Portable GUI backend for OpenJDK."),
        BootstrapComponent("caciocavallo 17", "Portable GUI backend for OpenJDK."),
        BootstrapComponent("Internal-17", "Java 17 Environment (required for Minecraft 1.17+)."),
        BootstrapComponent("Internal-21", "Java 21 Environment (required for Minecraft 1.20.5+)."),
        BootstrapComponent("Internal-25", "Java 25 Environment (required for Minecraft 25.1+)."),
        BootstrapComponent("Internal-8", "Java 8 Environment (required for Minecraft 1.16 and below)."),
        BootstrapComponent("JNA", "Enables Minecraft to directly call low-level OS functions."),
        BootstrapComponent("Launcher Components", "Essential launcher components."),
        BootstrapComponent("LWJGL 3.3.3", "Lightweight Java Game Library (required by Minecraft)."),
    )

    private fun bootstrapPrefs() = getSharedPreferences("droid_launcher_bootstrap", MODE_PRIVATE)

    private fun bootstrapComplete(): Boolean = bootstrapPrefs().getBoolean("components_extracted", false)

    private fun bootstrapRoot(): java.io.File = java.io.File(filesDir, "launcher-components")

    private fun bootstrapAssetCandidates(name: String): List<String> {
        val safe = name.replace(" ", "_").replace("/", "_")
        return listOf("launcher_components/$name", "launcher_components/$safe")
    }

    private fun copyAssetTree(assetPath: String, destination: java.io.File): Int {
        val children = assets.list(assetPath) ?: emptyArray()
        if (children.isEmpty()) {
            assets.open(assetPath).use { input ->
                destination.parentFile?.mkdirs()
                java.io.BufferedOutputStream(java.io.FileOutputStream(destination)).use { output ->
                    input.copyTo(output)
                }
            }
            return 1
        }
        destination.mkdirs()
        var count = 0
        for (child in children) {
            count += copyAssetTree("$assetPath/$child", java.io.File(destination, child))
        }
        return count
    }

    private fun findBootstrapAsset(name: String): String? {
        for (candidate in bootstrapAssetCandidates(name)) {
            try {
                assets.list(candidate)
                assets.open(candidate).close()
                return candidate
            } catch (_: Exception) {
                // It may be a directory. list() is enough for directory assets.
                try {
                    val children = assets.list(candidate)
                    if (children != null && children.isNotEmpty()) return candidate
                } catch (_: Exception) { }
            }
        }
        return null
    }

    private fun verifyBootstrapExtraction(): Boolean {
        val root = bootstrapRoot()
        return bootstrapComponents.all { component ->
            val marker = java.io.File(root, component.name.replace(" ", "_") + ".installed")
            marker.isFile && marker.length() > 0L
        }
    }

    private fun extractBootstrapComponents(onResult: (Boolean, String) -> Unit) {
        Thread {
            try {
                val root = bootstrapRoot()
                root.mkdirs()
                val missing = mutableListOf<String>()
                var extracted = 0
                for (component in bootstrapComponents) {
                    val asset = findBootstrapAsset(component.name)
                    if (asset == null) {
                        missing += component.name
                        continue
                    }
                    val target = java.io.File(root, component.name.replace(" ", "_") + ".bundle")
                    target.deleteRecursively()
                    val count = copyAssetTree(asset, target)
                    if (count <= 0) throw java.io.IOException("Empty asset: ${component.name}")
                    java.io.File(root, component.name.replace(" ", "_") + ".installed").writeText(count.toString())
                    extracted++
                }
                if (missing.isNotEmpty()) {
                    throw java.io.FileNotFoundException("Missing bundled components: ${missing.joinToString(", ")}")
                }
                if (!verifyBootstrapExtraction() || extracted != bootstrapComponents.size) {
                    throw java.io.IOException("Component extraction verification failed")
                }
                bootstrapPrefs().edit().putBoolean("components_extracted", true).apply()
                runOnUiThread { onResult(true, "All ${bootstrapComponents.size} components were extracted and verified.") }
            } catch (error: Throwable) {
                bootstrapPrefs().edit().putBoolean("components_extracted", false).apply()
                runOnUiThread { onResult(false, error.message ?: "Unknown extraction error") }
            }
        }.start()
    }

    private fun showBootstrapGate() {
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(24), dp(18), dp(24), dp(18))
            setBackgroundColor(bg)
        }
        val left = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(8), dp(4), dp(18), dp(4))
        }
        val header = label("Zalith Launcher", 26f, true)
        left.addView(header, LinearLayout.LayoutParams(-1, dp(58)))
        val subtitle = label("Launcher Components", 18f, true)
        left.addView(subtitle, LinearLayout.LayoutParams(-1, dp(48)))

        val listScroll = ScrollView(this).apply { isFillViewport = true }
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        bootstrapComponents.forEach { component ->
            val row = cardView(10)
            row.setPadding(dp(12), dp(7), dp(12), dp(7))
            row.addView(label(component.name, 15f, true))
            row.addView(label(component.description, 11f, false))
            list.addView(row, LinearLayout.LayoutParams(-1, dp(67)))
        }
        listScroll.addView(list)
        left.addView(listScroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(left, LinearLayout.LayoutParams(0, -1, 0.67f))

        val right = cardView(16).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(22), dp(22), dp(22), dp(22))
        }
        right.addView(label("The launcher needs to install these files to ensure Minecraft runs properly.", 15f, true))
        right.addView(label("They are included in the app and must be extracted first. Click the button below to start extraction and update.", 13f, false))
        val status = label("Ready to install", 13f, false)
        status.setPadding(0, dp(18), 0, dp(18))
        right.addView(status)
        val install = button("Install", true)
        install.textSize = 18f
        install.setOnClickListener {
            install.isEnabled = false
            install.text = "Installing…"
            status.text = "Extracting and verifying launcher components…"
            extractBootstrapComponents { success, message ->
                if (success) {
                    status.text = message
                    install.text = "Installed"
                    Toast.makeText(this, "Launcher components installed", Toast.LENGTH_LONG).show()
                    showPage("Game")
                } else {
                    install.isEnabled = true
                    install.text = "Install"
                    status.text = "Installation failed: $message"
                    Toast.makeText(this, "Component installation failed", Toast.LENGTH_LONG).show()
                }
            }
        }
        right.addView(install, LinearLayout.LayoutParams(-1, dp(64)))
        root.addView(right, LinearLayout.LayoutParams(0, -1, 0.33f))
        setContentView(root)
    }

'''

INIT = r'''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        if (bootstrapComplete()) {
            buildUi()
            showPage("Game")
        } else {
            showBootstrapGate()
        }
    }

'''

BUILD_UI = r'''    private fun buildUi() {
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(bg)
        }
        val top = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(14), dp(4), dp(10), dp(4))
        }
        title.text = "Droid Launcher"
        title.textSize = 20f
        title.setTextColor(text)
        title.typeface = Typeface.DEFAULT_BOLD
        top.addView(title, LinearLayout.LayoutParams(0, dp(52), 1f))
        val home = button("⌂")
        home.setOnClickListener { showPage("Game") }
        val accounts = button("♟")
        accounts.setOnClickListener { showPage("Accounts") }
        val downloads = button("⇩")
        downloads.setOnClickListener { showPage("Search by ID") }
        val settings = button("⚙")
        settings.setOnClickListener { showPage("Renderer") }
        listOf(home, accounts, downloads, settings).forEach {
            top.addView(it, LinearLayout.LayoutParams(dp(52), dp(52)))
        }
        root.addView(top, LinearLayout.LayoutParams(-1, dp(60)))
        val body = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(12), dp(6), dp(12), dp(12))
        }
        val scroll = ScrollView(this).apply { isFillViewport = true }
        scroll.addView(pageArea)
        pageArea.orientation = LinearLayout.VERTICAL
        pageArea.setPadding(dp(2), dp(2), dp(2), dp(10))
        body.addView(scroll, LinearLayout.LayoutParams(0, -1, 1f))
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
    }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    s = ui.read_text(encoding="utf-8")

    # Ensure Android imports exist; this source already uses these in the generated UI,
    # but add them defensively for older base variants.
    if "import android.os.Bundle" not in s:
        s = s.replace("package com.example.launcher\n", "package com.example.launcher\n\nimport android.os.Bundle\n", 1)

    s = replace_method(s, "    private fun buildUi()", BUILD_UI)

    if "private fun showBootstrapGate()" not in s:
        anchor = "    private fun buildUi()"
        s = s.replace(anchor, HELPERS + "\n" + anchor, 1)
    else:
        raise SystemExit("[step287] bootstrap gate already exists; refusing duplicate insertion")

    # Replace the existing onCreate only if it is present. Otherwise add one before helpers.
    if "    override fun onCreate(savedInstanceState: Bundle?)" in s:
        s = replace_method(s, "    override fun onCreate(savedInstanceState: Bundle?)", INIT.rstrip())
    else:
        anchor = "    private data class BootstrapComponent"
        s = s.replace(anchor, INIT + "\n" + anchor, 1)

    ui.write_text(s, encoding="utf-8")
    print("[step287] isolated first-run Zalith Launcher component GUI installed")
    print("[step287] no Home/Accounts/Downloads/Settings navigation is rendered on the gate")
    print("[step287] completion persists only after all bundled components extract and verify")
    print("[step287] failed/abandoned installation remains gated on next launch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
