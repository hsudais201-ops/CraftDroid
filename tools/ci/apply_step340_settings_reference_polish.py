#!/usr/bin/env python3
"""Step 340: polish the generated Settings/Renderer shell to mirror 2.jpeg."""
from pathlib import Path
import sys

MARKER = "// STEP340_SETTINGS_REFERENCE_POLISH"


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step340] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step340] settings reference polish already present")
        return 0

    # Match the pale-blue selected Settings pill visible in 2.jpeg.
    old = '''        listOf("▣", "♟", "⇩", "⚙").forEach { icon ->\n            val b = button(icon)\n            top.addView(b, LinearLayout.LayoutParams(dp(48), dp(48)))\n            if (icon == "⚙") b.setOnClickListener { showPage("Renderer") }\n        }'''
    new = '''        listOf("▣", "♟", "⇩", "⚙").forEach { icon ->\n            val b = button(if (icon == "⚙") "⚙  Settings" else icon)\n            if (icon == "⚙") {\n                b.setTextColor(accent)\n                b.textSize = 13f\n                b.background = android.graphics.drawable.GradientDrawable().apply {\n                    setColor(Color.rgb(231, 240, 249))\n                    cornerRadius = dp(14).toFloat()\n                }\n                b.setPadding(dp(10), 0, dp(10), 0)\n                b.setOnClickListener { showPage("Renderer") }\n                top.addView(b, LinearLayout.LayoutParams(dp(112), dp(44)).apply { setMargins(dp(4), 0, 0, 0) })\n            } else {\n                top.addView(b, LinearLayout.LayoutParams(dp(48), dp(48)))\n            }\n        }'''
    if old not in s:
        raise SystemExit("[step340] header icon block not found")
    s = s.replace(old, new, 1)

    # Make the Renderer rail item visibly selected like the reference.
    old = '''            val b = button("$icon\\n$page")\n            b.textSize = 10f\n            b.gravity = Gravity.CENTER\n            b.setOnClickListener { showPage(page) }\n            rail.addView(b, LinearLayout.LayoutParams(dp(92), dp(62)))'''
    new = '''            val b = button("$icon\\n$page")\n            b.textSize = 10f\n            b.gravity = Gravity.CENTER\n            if (page == "Renderer") {\n                b.setTextColor(accent)\n                b.background = android.graphics.drawable.GradientDrawable().apply {\n                    setColor(Color.rgb(231, 240, 249))\n                    cornerRadius = dp(14).toFloat()\n                }\n            }\n            b.setOnClickListener { showPage(page) }\n            rail.addView(b, LinearLayout.LayoutParams(dp(92), dp(62)))'''
    if old not in s:
        raise SystemExit("[step340] navigation block not found")
    s = s.replace(old, new, 1)

    # Keep the reference wording, including its compact fullscreen copy.
    s = s.replace('Higher values improve quality. Adjust according to your needs',
                  'higher values improve quality. Adjust according to your needs', 1)
    s = s.replace('Enable fullscreen mode, ignoring safe areas like notches and punch-holes.',
                  'Enable fullscreen mode, ignoring safe areas like notches end punch-holes.', 1)

    # Explicitly mark the finalized generated source without changing runtime behavior.
    s = s.replace('    private fun rendererPage() {',
                  '    private fun rendererPage() {\n        // STEP340_SETTINGS_REFERENCE_POLISH', 1)
    ui.write_text(s, encoding="utf-8")
    print("[step340] Settings/Renderer shell polished to match 2.jpeg")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
