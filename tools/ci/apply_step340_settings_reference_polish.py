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

    changed = False

    # Match the pale-blue selected Settings pill visible in 2.jpeg.
    old = '''        listOf("▣", "♟", "⇩", "⚙").forEach { icon ->
            val b = button(icon)
            top.addView(b, LinearLayout.LayoutParams(dp(48), dp(48)))
            if (icon == "⚙") b.setOnClickListener { showPage("Renderer") }
        }'''
    new = '''        listOf("▣", "♟", "⇩", "⚙").forEach { icon ->
            val b = button(if (icon == "⚙") "⚙  Settings" else icon)
            if (icon == "⚙") {
                b.setTextColor(accent)
                b.textSize = 13f
                b.background = android.graphics.drawable.GradientDrawable().apply {
                    setColor(Color.rgb(231, 240, 249))
                    cornerRadius = dp(14).toFloat()
                }
                b.setPadding(dp(10), 0, dp(10), 0)
                b.setOnClickListener { showPage("Renderer") }
                top.addView(b, LinearLayout.LayoutParams(dp(112), dp(44)).apply { setMargins(dp(4), 0, 0, 0) })
            } else {
                top.addView(b, LinearLayout.LayoutParams(dp(48), dp(48)))
            }
        }'''
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
    else:
        print("[step340] header icon block already transformed by an earlier final UI patch; preserving it")

    # Make the Renderer rail item visibly selected like the reference.
    old = '''            val b = button("$icon\\n$page")
            b.textSize = 10f
            b.gravity = Gravity.CENTER
            b.setOnClickListener { showPage(page) }
            rail.addView(b, LinearLayout.LayoutParams(dp(92), dp(62)))'''
    new = '''            val b = button("$icon\\n$page")
            b.textSize = 10f
            b.gravity = Gravity.CENTER
            if (page == "Renderer") {
                b.setTextColor(accent)
                b.background = android.graphics.drawable.GradientDrawable().apply {
                    setColor(Color.rgb(231, 240, 249))
                    cornerRadius = dp(14).toFloat()
                }
            }
            b.setOnClickListener { showPage(page) }
            rail.addView(b, LinearLayout.LayoutParams(dp(92), dp(62)))'''
    if old in s:
        s = s.replace(old, new, 1)
        changed = True
    else:
        print("[step340] navigation block already transformed by an earlier final UI patch; preserving it")

    # Keep the reference wording, including its compact fullscreen copy.
    replacements = [
        ('Higher values improve quality. Adjust according to your needs',
         'higher values improve quality. Adjust according to your needs'),
        ('Enable fullscreen mode, ignoring safe areas like notches and punch-holes.',
         'Enable fullscreen mode, ignoring safe areas like notches end punch-holes.'),
    ]
    for old_text, new_text in replacements:
        if old_text in s:
            s = s.replace(old_text, new_text, 1)
            changed = True

    # Explicitly mark the finalized generated source without changing runtime behavior.
    s = s.replace('    private fun rendererPage() {',
                  '    private fun rendererPage() {\n        // STEP340_SETTINGS_REFERENCE_POLISH', 1)
    ui.write_text(s, encoding="utf-8")
    print(f"[step340] Settings/Renderer shell polish finalized; changes={changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
