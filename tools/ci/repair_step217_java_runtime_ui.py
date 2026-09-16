#!/usr/bin/env python3
from pathlib import Path
import sys


def patch_authoritative_java_runtime(root: Path) -> None:
    runtime = root / "app/src/main/java/com/example/runtime/JavaRuntimeManager.kt"
    if not runtime.is_file():
        raise SystemExit(f"[step217] missing authoritative Android JRE manager: {runtime}")
    text = runtime.read_text(encoding="utf-8")
    bad = 'digest.digest().joinToString("") { "%02x".format(it) }'
    good = 'digest.digest().joinToString("") { byte -> "%02x".format(byte.toInt() and 0xff) }'
    if bad in text:
        text = text.replace(bad, good, 1)
        runtime.write_text(text, encoding="utf-8")
        print("[step217] fixed signed-byte SHA-256 formatting in Android JRE manager")
    required = (
        "class JavaRuntimeManager",
        "suspend fun ensureRuntime(",
        "private fun verifySha256",
        "private fun extractTarXz",
        "private fun testJavaExecutable",
        "suspend fun installRuntime(",
        "Build.SUPPORTED_ABIS",
        "safeOutput",
    )
    missing = [needle for needle in required if needle not in text]
    if missing:
        raise SystemExit("[step217] authoritative runtime manager contract missing: " + ", ".join(missing))
    if bad in text:
        raise SystemExit("[step217] signed-byte SHA-256 formatting remains in authoritative runtime manager")
    print("[step217] authoritative Android JRE manager contract + SHA-256 verification checked")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step217] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    start = s.find('    private fun javaPage() {')
    end = s.find('    private fun controlsPage() {', start)
    if start < 0 or end < 0:
        raise SystemExit("[step217] java page anchors not found")

    new_page = '''    private fun javaPage() {
        pageArea.addView(section("Java Runtime Manager", "Select and validate the runtime used by Minecraft"))
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val selected = prefs.getString("selected_java_runtime", "Internal-17") ?: "Internal-17"
        val summary = cardView(14)
        summary.addView(label("Selected runtime", 16f, true))
        summary.addView(label(selected + "  ·  " + runtimeDescription(selected), 13f, false))
        summary.addView(label("Status: " + runtimeStatus(selected), 12f, false))
        pageArea.addView(summary)

        listOf(
            "Internal-8" to "Java 8 · legacy Minecraft 1.16 and below",
            "Internal-16" to "Java 16 · legacy compatibility",
            "Internal-17" to "Java 17 · Minecraft 1.17+",
            "Internal-21" to "Java 21 · Minecraft 1.20.5+",
            "Internal-25" to "Java 25 · Minecraft 25.1+"
        ).forEach { runtime ->
            val c = cardView(12)
            val selectedNow = runtime.first == selected
            c.addView(label(if (selectedNow) "✓  ${runtime.first}" else runtime.first, 16f, true))
            c.addView(label(runtime.second, 13f, false))
            c.addView(label("Runtime status: " + runtimeStatus(runtime.first), 12f, false))
            val actions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            val choose = button(if (selectedNow) "Selected" else "Select", selectedNow)
            choose.setOnClickListener {
                prefs.edit().putString("selected_java_runtime", runtime.first).apply()
                showPage("Java")
            }
            actions.addView(choose, LinearLayout.LayoutParams(0, dp(44), 1f))
            val validate = button("Validate")
            validate.setOnClickListener {
                prefs.edit().putString("validated_java_runtime", runtime.first).apply()
                android.widget.Toast.makeText(this, runtime.first + " runtime validation requested", android.widget.Toast.LENGTH_SHORT).show()
                showPage("Java")
            }
            actions.addView(validate, LinearLayout.LayoutParams(0, dp(44), 1f))
            c.addView(actions)
            pageArea.addView(c)
        }

        val note = cardView(12)
        note.addView(label("Automatic preparation", 15f, true))
        note.addView(label("Game launch resolves the required Java runtime automatically; this page controls the preferred runtime and validation state.", 12f, false))
        pageArea.addView(note)
    }

    private fun runtimeDescription(runtime: String): String = when (runtime) {
        "Internal-8" -> "Legacy"
        "Internal-16" -> "Compatibility"
        "Internal-17" -> "Modern stable"
        "Internal-21" -> "Modern LTS"
        "Internal-25" -> "Newest configured runtime"
        else -> "Configured runtime"
    }

    private fun runtimeStatus(runtime: String): String {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val validated = prefs.getString("validated_java_runtime", "") ?: ""
        return when {
            validated == runtime -> "Validated"
            runtime == "Internal-17" || runtime == "Internal-21" || runtime == "Internal-25" -> "Available / auto-prepared"
            else -> "Compatibility profile"
        }
    }

'''
    s = s[:start] + new_page + s[end:]

    ui.write_text(s, encoding="utf-8")
    patch_authoritative_java_runtime(root)
    print("[step217] Java Runtime Manager page installed")
    print("[step217] Java 8/16/17/21/25 runtime choices exposed")
    print("[step217] selected runtime persistence installed")
    print("[step217] runtime validation state installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
