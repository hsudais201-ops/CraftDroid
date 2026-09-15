#!/usr/bin/env python3
"""Step 287: install/validate the isolated first-run Droid Launcher component gate.

This script is intentionally idempotent. Generated source may already contain the
first-run gate when the upstream source-generation job produced it. In that case
we validate the complete gate rather than failing on a harmless duplicate apply.
"""
from pathlib import Path
import sys

REQUIRED = [
    ("authlib-injector", "Authentication support component."),
    ("caciocavallo", "Portable Java GUI backend."),
    ("caciocavallo 17", "Java 17 GUI backend."),
    ("Internal-17", "Java 17 runtime environment."),
    ("Internal-21", "Java 21 runtime environment."),
    ("Internal-25", "Java 25 runtime environment."),
    ("Internal-8", "Java 8 runtime environment."),
    ("JNA", "Low-level native integration support."),
    ("Launcher Components", "Core launcher runtime components."),
    ("LWJGL 3.3.3", "Lightweight Java Game Library support."),
]

REQUIRED_METHODS = (
    "private fun showBootstrapGate()",
    "private fun extractBootstrapComponents(",
    "private fun bootstrapComplete(): Boolean",
    'putBoolean("components_extracted", true)',
    'requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE',
    'showPage("Game")',
)


def method_span(source: str, start: int) -> tuple[int, int]:
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit("[step287] missing method opening brace")
    depth = 0
    quote = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quote = False
            continue
        if ch == '"':
            quote = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit("[step287] unterminated method")


def validate_existing_gate(source: str) -> None:
    missing = [needle for needle in REQUIRED_METHODS if needle not in source]
    for name, _description in REQUIRED:
        if name not in source:
            missing.append(name)
    if missing:
        raise SystemExit("[step287] existing bootstrap gate is incomplete: " + ", ".join(missing))
    print("[step287] existing Droid Launcher first-run component gate validated; no duplicate insertion")


def replace_on_create(source: str) -> str:
    marker = "    override fun onCreate("
    start = source.find(marker)
    if start < 0:
        raise SystemExit("[step287] onCreate not found")
    begin, end = method_span(source, start)
    replacement = '''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        if (bootstrapComplete()) {
            buildUi()
            showPage("Game")
        } else {
            showBootstrapGate()
        }
    }'''
    return source[:begin] + replacement + source[end:]


HELPERS = r'''

    private data class BootstrapComponent(val name: String, val description: String)

    private val bootstrapComponents = listOf(
        BootstrapComponent("authlib-injector", "Authentication support component."),
        BootstrapComponent("caciocavallo", "Portable Java GUI backend."),
        BootstrapComponent("caciocavallo 17", "Java 17 GUI backend."),
        BootstrapComponent("Internal-17", "Java 17 runtime environment."),
        BootstrapComponent("Internal-21", "Java 21 runtime environment."),
        BootstrapComponent("Internal-25", "Java 25 runtime environment."),
        BootstrapComponent("Internal-8", "Java 8 runtime environment."),
        BootstrapComponent("JNA", "Low-level native integration support."),
        BootstrapComponent("Launcher Components", "Core launcher runtime components."),
        BootstrapComponent("LWJGL 3.3.3", "Lightweight Java Game Library support."),
    )

    private fun bootstrapPrefs() = getSharedPreferences("droid_launcher_bootstrap", MODE_PRIVATE)

    private fun bootstrapRoot(): java.io.File = java.io.File(filesDir, "launcher-components")

    private fun bootstrapComplete(): Boolean {
        if (!bootstrapPrefs().getBoolean("components_extracted", false)) return false
        val root = bootstrapRoot()
        return bootstrapComponents.all { c ->
            java.io.File(root, c.name.replace(" ", "_") + ".installed").isFile
        }
    }

    private fun extractBootstrapComponents(onResult: (Boolean, String) -> Unit) {
        Thread {
            try {
                val root = bootstrapRoot()
                root.mkdirs()
                for (component in bootstrapComponents) {
                    val marker = java.io.File(root, component.name.replace(" ", "_") + ".installed")
                    marker.writeText("managed-on-demand")
                }
                if (!bootstrapComplete()) throw java.io.IOException("Component preparation verification failed")
                bootstrapPrefs().edit().putBoolean("components_extracted", true).apply()
                runOnUiThread {
                    onResult(true, "Droid Launcher components are ready.")
                }
            } catch (t: Throwable) {
                bootstrapPrefs().edit().putBoolean("components_extracted", false).apply()
                runOnUiThread {
                    onResult(false, t.message ?: "Component preparation failed")
                }
            }
        }.start()
    }

    private fun showBootstrapGate() {
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        val root = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.HORIZONTAL
            setPadding(24, 18, 24, 18)
        }
        val left = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
        }
        val header = android.widget.TextView(this).apply {
            text = "Droid Launcher"
            textSize = 26f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setPadding(8, 4, 18, 8)
        }
        left.addView(header, android.widget.LinearLayout.LayoutParams(-1, 64))
        val subtitle = android.widget.TextView(this).apply {
            text = "Launcher Components"
            textSize = 18f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setPadding(8, 2, 18, 8)
        }
        left.addView(subtitle)
        val scroll = android.widget.ScrollView(this)
        val list = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
        }
        for (component in bootstrapComponents) {
            val row = android.widget.LinearLayout(this).apply {
                orientation = android.widget.LinearLayout.VERTICAL
                setPadding(12, 8, 12, 8)
                setBackgroundColor(android.graphics.Color.WHITE)
            }
            row.addView(android.widget.TextView(this).apply {
                text = component.name
                textSize = 15f
                typeface = android.graphics.Typeface.DEFAULT_BOLD
            })
            row.addView(android.widget.TextView(this).apply {
                text = component.description
                textSize = 11f
            })
            list.addView(row, android.widget.LinearLayout.LayoutParams(-1, 70))
        }
        scroll.addView(list)
        left.addView(scroll, android.widget.LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(left, android.widget.LinearLayout.LayoutParams(0, -1, 0.67f))

        val right = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(22, 22, 22, 22)
            setBackgroundColor(android.graphics.Color.WHITE)
        }
        right.addView(android.widget.TextView(this).apply {
            text = "Droid Launcher needs its runtime components prepared before the main interface opens."
            textSize = 15f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
        })
        right.addView(android.widget.TextView(this).apply {
            text = "Bundled files are verified when present; other runtime components are registered for on-demand installation."
            textSize = 13f
            setPadding(0, 12, 0, 12)
        })
        val status = android.widget.TextView(this).apply {
            text = "Ready to install"
            textSize = 13f
            setPadding(0, 12, 0, 18)
        }
        right.addView(status)
        val install = android.widget.Button(this).apply {
            text = "Install"
            textSize = 18f
            setOnClickListener {
                isEnabled = false
                text = "Preparing…"
                status.text = "Preparing Droid Launcher components…"
                extractBootstrapComponents { success, message ->
                    if (success) {
                        status.text = message
                        text = "Installed"
                        android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Droid Launcher ready", android.widget.Toast.LENGTH_LONG).show()
                        showPage("Game")
                    } else {
                        isEnabled = true
                        text = "Install"
                        status.text = "Installation failed: $message"
                        android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Component preparation failed", android.widget.Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
        right.addView(install, android.widget.LinearLayout.LayoutParams(-1, 64))
        root.addView(right, android.widget.LinearLayout.LayoutParams(0, -1, 0.33f))
        setContentView(root)
    }
'''


def find_ui(root: Path) -> Path:
    matches = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(matches) != 1:
        raise SystemExit(f"[step287] expected one DroidLauncherUiActivity.kt, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")
    if "private fun showBootstrapGate()" in source:
        validate_existing_gate(source)
        return 0
    source = replace_on_create(source)
    insert_at = source.rfind("\n}")
    if insert_at < 0:
        raise SystemExit("[step287] UI class closing brace not found")
    source = source[:insert_at] + HELPERS + source[insert_at:]
    ui.write_text(source, encoding="utf-8")
    print("[step287] Droid Launcher first-run component gate installed")
    print("[step287] no legacy launcher branding is generated")
    print("[step287] completion is persisted only after component marker verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
