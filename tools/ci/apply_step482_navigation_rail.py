#!/usr/bin/env python3
"""Step 482: replace cramped top navigation with a premium persistent navigation rail."""
from pathlib import Path
import sys

MARKER = "// STEP482_NAVIGATION_RAIL"

def span(src, sig):
    a = src.find(sig)
    if a < 0:
        raise SystemExit("[step482] missing " + sig)
    brace = src.find("{", a)
    if brace < 0:
        raise SystemExit("[step482] missing brace " + sig)
    depth = 0
    state = "code"
    esc = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
        if state == "line":
            if c == "\n": state = "code"
            i += 1; continue
        if state == "block":
            if c == "*" and n == "/": state = "code"; i += 2
            else: i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"': state = "code"; i += 3
            else: i += 1
            continue
        if state == "string":
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': state = "code"
            i += 1; continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = "triple"; i += 3; continue
        if c == '"': state = "string"; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return a, i + 1
        i += 1
    raise SystemExit("[step482] unterminated " + sig)

def replace(src, sig, new):
    a, b = span(src, sig)
    return src[:a] + new + src[b:]

HELPERS = r'''
    // STEP482_NAVIGATION_RAIL
    private fun step482NavItem(labelText: String, action: () -> Unit): TextView =
        TextView(this).apply {
            text = labelText
            textSize = 13f
            gravity = Gravity.CENTER_VERTICAL
            setTextColor(android.graphics.Color.argb(232, 230, 245, 245))
            setPadding(dp(14), 0, dp(8), 0)
            isClickable = true
            isFocusable = true
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(13).toFloat()
                setColor(android.graphics.Color.argb(55, 45, 210, 160))
                setStroke(dp(1), android.graphics.Color.argb(65, 80, 235, 180))
            }
            setOnClickListener { action() }
        }
'''

BUILD = r'''    private fun buildUi() {
        val root = android.widget.FrameLayout(this)
        val bg = android.widget.ImageView(this).apply {
            scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
            setBackgroundColor(android.graphics.Color.rgb(7, 11, 18))
        }
        root.addView(bg, android.widget.FrameLayout.LayoutParams(-1, -1))
        root.addView(android.view.View(this).apply {
            setBackgroundColor(android.graphics.Color.argb(190, 4, 8, 15))
        }, android.widget.FrameLayout.LayoutParams(-1, -1))
        val glow = android.view.View(this).apply {
            background = android.graphics.drawable.GradientDrawable().apply {
                colors = intArrayOf(
                    android.graphics.Color.argb(60, 35, 245, 170),
                    android.graphics.Color.TRANSPARENT
                )
                orientation = android.graphics.drawable.GradientDrawable.Orientation.TL_BR
            }
        }
        root.addView(glow, android.widget.FrameLayout.LayoutParams(-1, -1))

        val shell = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(dp(10), dp(10), dp(10), dp(10))
        }

        val rail = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), dp(10), dp(10), dp(10))
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(20).toFloat()
                setColor(android.graphics.Color.argb(235, 9, 16, 25))
                setStroke(dp(1), android.graphics.Color.argb(95, 70, 235, 175))
            }
            elevation = if (step376LowRam) dp(1).toFloat() else dp(5).toFloat()
            addView(step460LogoBadge("CD", 54), LinearLayout.LayoutParams(dp(54), dp(54)))
            addView(step375Text("CRAFTDROID", 14f, true).apply {
                setPadding(0, dp(9), 0, dp(2))
            })
            addView(step375Text("Minecraft Java", 10f).apply {
                setTextColor(android.graphics.Color.argb(165, 195, 220, 228))
                setPadding(0, 0, 0, dp(10))
            })
        }

        val destinations = listOf(
            "⌂  Home" to "Home",
            "▣  Instances" to "Instances",
            "◈  Content" to "Content",
            "◉  Servers" to "Servers",
            "♟  Accounts" to "Accounts",
            "J  Java" to "Java",
            "⚙  Settings" to "Settings"
        )
        destinations.forEach { pair ->
            rail.addView(step482NavItem(pair.first) { showPage(pair.second) },
                LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(6) })
        }
        rail.addView(android.view.View(this), LinearLayout.LayoutParams(1, 0, 1f))
        rail.addView(step375Text("Premium launcher surface", 9.5f).apply {
            setTextColor(android.graphics.Color.argb(130, 190, 210, 220))
            gravity = Gravity.CENTER
            setPadding(0, dp(4), 0, dp(4))
        })

        shell.addView(rail, LinearLayout.LayoutParams(dp(210), -1))

        val contentShell = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(10), 0, 0, 0)
        }
        val top = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), 0, dp(12), 0)
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(16).toFloat()
                setColor(android.graphics.Color.argb(180, 11, 18, 28))
                setStroke(dp(1), android.graphics.Color.argb(55, 80, 235, 180))
            }
            addView(step375Text("LAUNCHER", 11f, true), LinearLayout.LayoutParams(0, dp(44), 1f))
            addView(step375Text("Low-RAM optimized", 9.5f).apply {
                setTextColor(android.graphics.Color.rgb(86, 240, 177))
            })
        }
        contentShell.addView(top, LinearLayout.LayoutParams(-1, dp(48)))

        val scroll = android.widget.ScrollView(this).apply {
            isFillViewport = true
            isVerticalScrollBarEnabled = false
        }
        pageArea.orientation = LinearLayout.VERTICAL
        pageArea.setPadding(dp(2), dp(10), dp(2), dp(18))
        scroll.addView(pageArea)
        contentShell.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        shell.addView(contentShell, LinearLayout.LayoutParams(0, -1, 1f))
        root.addView(shell, android.widget.FrameLayout.LayoutParams(-1, -1))
        setContentView(root)
        step376LoadBackground(bg)
        step376StartGlow(glow)
    }
'''

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step482] UI missing")
    s = ui.read_text(encoding="utf-8")
    if MARKER not in s:
        pos = s.find("    private fun buildUi()")
        if pos < 0:
            raise SystemExit("[step482] buildUi anchor missing")
        s = s[:pos] + HELPERS + "\n" + s[pos:]
    s = replace(s, "    private fun buildUi()", BUILD)
    for needle in ("// STEP482_NAVIGATION_RAIL", "private fun step482NavItem", "Low-RAM optimized", "Settings"):
        if needle not in s:
            raise SystemExit("[step482] missing contract " + needle)
    ui.write_text(s, encoding="utf-8")
    print("[step482] premium persistent navigation rail installed")

if __name__ == "__main__":
    main()
