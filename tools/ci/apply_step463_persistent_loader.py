#!/usr/bin/env python3
"""Step 463: wire the polished loader UI to persistent per-instance state."""
from pathlib import Path
import subprocess
import sys

UI_NAME = "DroidLauncherUiActivity.kt"
MARKER = "// STEP463_PERSISTENT_LOADER_SELECTOR"


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob(UI_NAME))
    if len(hits) != 1:
        raise SystemExit(f"[step463] expected one {UI_NAME}, found {len(hits)}")
    return hits[0]


def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit("[step463] missing " + signature)
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit("[step463] missing opening brace")
    depth = 0
    quote = False
    triple = False
    escaped = False
    i = brace
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ""
        n2 = source[i + 2] if i + 2 < len(source) else ""
        if triple:
            if c == '"' and n == '"' and n2 == '"':
                triple = False
                i += 3
            else:
                i += 1
            continue
        if quote:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                quote = False
            i += 1
            continue
        if c == '"' and n == '"' and n2 == '"':
            triple = True
            i += 3
            continue
        if c == '"':
            quote = True
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise SystemExit("[step463] unterminated " + signature)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")

    if MARKER in source:
        print("[step463] persistent loader selector already applied")
        return 0

    helpers = r'''
    // STEP463_PERSISTENT_LOADER_SELECTOR
    private fun step463LoaderPrefs() =
        getSharedPreferences("droid_launcher_loader", MODE_PRIVATE)

    private fun step463LoaderKey(): String =
        "loader:" + step375SelectedInstance().ifBlank { "global" }

    private fun step463SelectedLoader(): String =
        step463LoaderPrefs().getString(step463LoaderKey(), "Fabric")?.trim()
            .takeUnless { it.isNullOrBlank() } ?: "Fabric"

    private fun step463SelectLoader() {
        val choices = arrayOf("Vanilla", "Fabric", "Forge", "NeoForge", "Quilt")
        val selected = step463SelectedLoader()
        android.app.AlertDialog.Builder(this)
            .setTitle("Select loader")
            .setSingleChoiceItems(choices, choices.indexOf(selected).coerceAtLeast(0)) { dialog, which ->
                val value = choices[which]
                step463LoaderPrefs().edit().putString(step463LoaderKey(), value).apply()
'''
    if "private var selectedLoader" in source:
        helpers += r'''                selectedLoader = value
'''
    helpers += r'''                dialog.dismiss()
                android.widget.Toast.makeText(
                    this,
                    value + " selected for " + step375SelectedInstance().ifBlank { "global" },
                    android.widget.Toast.LENGTH_SHORT
                ).show()
                showPage(currentPage)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
'''

    insert_anchor = "    private fun step460LoaderStrip(): android.widget.HorizontalScrollView ="
    pos = source.find(insert_anchor)
    if pos < 0:
        raise SystemExit("[step463] step460 loader-strip anchor missing")
    source = source[:pos] + helpers + "\n" + source[pos:]

    start, end = method_span(source, insert_anchor)
    block = source[start:end]

    old_prefix = '                            "Loader",'
    if old_prefix not in block:
        raise SystemExit("[step463] loader card detail anchor missing")

    # Convert each mod-loader card from a toast-only action to the real dialog.
    block = block.replace(
        old_prefix + '\n                            {\n                                android.widget.Toast.makeText(',
        old_prefix + '\n                            {\n                                step463SelectLoader()\n                                /*',
        5,
    )

    # The replacement above intentionally opens a block comment only if the old
    # structure exactly matched all five generated cards; otherwise use a safer
    # whole-method rewrite below.
    if "/*" in block:
        # Rebuild the entire loader list deterministically.
        methods = r'''    private fun step460LoaderStrip(): android.widget.HorizontalScrollView =
        android.widget.HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            val row = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                listOf(
                    "V" to "Vanilla",
                    "F" to "Fabric",
                    "F" to "Forge",
                    "N" to "NeoForge",
                    "Q" to "Quilt"
                ).forEach { pair ->
                    val isSelected = step463SelectedLoader().equals(pair.second, ignoreCase = true)
                    addView(
                        step460CategoryCard(
                            pair.first,
                            pair.second + if (isSelected) " ✓" else "",
                            if (isSelected) "Selected loader" else "Loader",
                            { step463SelectLoader() }
                        ),
                        LinearLayout.LayoutParams(dp(154), dp(68)).apply { marginEnd = dp(7) }
                    )
                }
                addView(
                    step460CategoryCard("JAVA", "Java", "Runtime", { showPage("Java") }),
                    LinearLayout.LayoutParams(dp(154), dp(68))
                )
            }
            addView(row)
        }
'''
        source = source[:start] + methods + source[end:]
    else:
        # Unexpected generator variant: patch action expressions conservatively.
        block = block.replace(
            'android.widget.Toast.makeText(\n                                    this@DroidLauncherUiActivity,\n                                    pair.second + " selected for the current instance.",\n                                    android.widget.Toast.LENGTH_SHORT\n                                ).show()',
            'step463SelectLoader()',
            5,
        )
        source = source[:start] + block + source[end:]

    ui.write_text(source, encoding="utf-8")
    premium = Path.cwd() / "tools/ci/apply_step479_premium_ui.py"
    if not premium.is_file():
        raise SystemExit("[step479] premium UI script missing")
    subprocess.run([sys.executable, str(premium), str(root)], check=True)
    verifier = Path.cwd() / "tools/ci/verify_step479_premium_ui.py"
    if not verifier.is_file():
        raise SystemExit("[step479] premium UI verifier missing")
    subprocess.run([sys.executable, str(verifier), str(root)], check=True)

    functional = Path.cwd() / "tools/ci/apply_step480_functional_managers.py"
    functional_verifier = Path.cwd() / "tools/ci/verify_step480_functional_managers.py"
    if not functional.is_file() or not functional_verifier.is_file():
        raise SystemExit("[step480] functional manager scripts missing")
    subprocess.run([sys.executable, str(functional), str(root)], check=True)
    subprocess.run([sys.executable, str(functional_verifier), str(root)], check=True)

    print("[step463] loader cards now persist a real per-instance selection and reuse the existing selectedLoader state when available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
