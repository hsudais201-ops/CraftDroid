#!/usr/bin/env python3
"""Step 382: remove dead Settings actions and make the visible settings honest.

Renderer/driver/API rows become descriptive device-adaptive settings; the two
controls with real local behavior remain interactive: render scale and fullscreen.
"""
from pathlib import Path
import sys

UI = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")


def span(src: str, sig: str):
    start = src.find(sig)
    if start < 0:
        raise SystemExit("[step382] missing method: " + sig)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("[step382] missing opening brace")
    depth = 0
    quote = False
    escaped = False
    i = brace
    while i < len(src):
        c = src[i]
        if quote:
            if escaped:
                escaped = False
            elif c == "\\": 
                escaped = True
            elif c == '"':
                quote = False
            i += 1
            continue
        if c == '"':
            quote = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise SystemExit("[step382] unterminated method: " + sig)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / UI
    if not ui.is_file():
        raise SystemExit("[step382] generated UI missing")
    source = ui.read_text(encoding="utf-8")
    start, end = span(source, "    private fun step375Settings()")
    replacement = '''    private fun step375Settings() {
        pageArea.addView(step375Title("Settings", "Reference 2 · device-adaptive renderer and performance controls."))

        val profile = com.example.renderer.PerformanceProfile.detect(this)
        val tierText = when (profile.tier) {
            com.example.renderer.PerformanceProfile.Tier.LOW -> "Low-RAM profile"
            com.example.renderer.PerformanceProfile.Tier.BALANCED -> "Balanced profile"
            com.example.renderer.PerformanceProfile.Tier.HIGH -> "High-performance profile"
        }
        val profileCard = step375Panel(12)
        profileCard.addView(step375Text("Device Performance", 16f, true))
        profileCard.addView(step375Text(tierText, 15f, true))
        profileCard.addView(step375Text("Target FPS: " + profile.targetFps + " · Render scale baseline: " + (profile.renderScale * 100).toInt() + "%", 12f))
        profileCard.addView(step375Text("JVM memory is clamped by available device memory before launch.", 12f).apply {
            setTextColor(android.graphics.Color.argb(190, 210, 230, 240))
        })
        pageArea.addView(profileCard, LinearLayout.LayoutParams(-1, dp(118)).apply { bottomMargin = dp(7) })

        listOf(
            "Global Renderer" to "Automatic · device adaptive",
            "Vulkan Driver" to "Automatic · use supported driver",
            "Graphics API" to "Automatic · use supported backend",
            "Resolution Rule" to "Percentage"
        ).forEach { (name, value) ->
            val p = step375Panel(12)
            p.addView(step375Text(name, 16f, true))
            p.addView(step375Text(value, 13f).apply {
                setTextColor(android.graphics.Color.argb(190, 210, 230, 240))
            })
            pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(78)).apply { bottomMargin = dp(7) })
        }

        val scaleCard = step375Panel(12)
        scaleCard.addView(step375Text("Resolution Scale", 16f, true))
        scaleCard.addView(step375Text("Lower values reduce GPU load and memory bandwidth.", 12f).apply {
            setTextColor(android.graphics.Color.argb(190, 210, 230, 240))
        })
        scaleCard.addView(android.widget.SeekBar(this).apply {
            max = 100
            progress = (step375Prefs().getInt("scale", 70) - 50).coerceIn(0, 50) * 2
            setOnSeekBarChangeListener(object : android.widget.SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(b: android.widget.SeekBar?, value: Int, fromUser: Boolean) {
                    val scale = 50 + (value / 2)
                    step375Prefs().edit().putInt("scale", scale).apply()
                }
                override fun onStartTrackingTouch(b: android.widget.SeekBar?) {}
                override fun onStopTrackingTouch(b: android.widget.SeekBar?) {}
            })
        })
        pageArea.addView(scaleCard, LinearLayout.LayoutParams(-1, dp(108)).apply { bottomMargin = dp(7) })

        val fullscreen = step375Panel(12)
        fullscreen.addView(android.widget.Switch(this).apply {
            text = "Game Fullscreen"
            textSize = 16f
            setTextColor(android.graphics.Color.WHITE)
            isChecked = step375Prefs().getBoolean("fullscreen", true)
            setOnCheckedChangeListener { _, value ->
                step375Prefs().edit().putBoolean("fullscreen", value).apply()
            }
        })
        fullscreen.addView(step375Text("Stored locally and applied to the game launch configuration when supported.", 11f).apply {
            setTextColor(android.graphics.Color.argb(175, 210, 230, 240))
        })
        pageArea.addView(fullscreen, LinearLayout.LayoutParams(-1, dp(82)))
    }'''
    source = source[:start] + replacement + source[end:]

    ui.write_text(source, encoding="utf-8")
    print("[step382] settings UI cleaned: no-op actions removed")
    print("[step382] low-RAM/balanced/high performance profile is now shown from the real PerformanceProfile detector")
    print("[step382] resolution scale and fullscreen remain interactive and persistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
