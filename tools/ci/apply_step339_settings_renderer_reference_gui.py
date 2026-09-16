#!/usr/bin/env python3
"""Step 339: reproduce the supplied 2.jpeg Settings · Renderer screen."""
from pathlib import Path
import re
import sys

MARKER = "// STEP339_SETTINGS_RENDERER_REFERENCE_GUI"

RENDERER_METHOD = r'''    private fun rendererPage() {
        // STEP339_SETTINGS_RENDERER_REFERENCE_GUI
        title.text = "Settings · Renderer"
        pageArea.setPadding(0, dp(2), dp(12), dp(12))

        val rendererCard = roundedCard(20)
        addReferenceSetting(rendererCard, "Global Renderer",
            "The global default renderer uses a dynamic library translation layer to ensure runs\nsmoothly on mobile devices",
            "Selected: Krypton Wrapper", true, "⇩") {
            showRendererChoiceDialog("Global Renderer", listOf("Krypton Wrapper", "ANGLE", "Zink"))
        }
        addReferenceSetting(rendererCard, "Vulkan Driver", "",
            "Selected: Turnip", true, "⇩") {
            showRendererChoiceDialog("Vulkan Driver", listOf("Turnip", "System", "Disabled"))
        }
        addReferenceSetting(rendererCard, "Graphics API",
            "Set the graphics API used by Minecraft 26.2+",
            "Selected: Only set to OpenGL on First launch", false, "⌄") {
            showRendererChoiceDialog("Graphics API", listOf("Only set to OpenGL on First launch", "OpenGL", "Vulkan", "Automatic"))
        }
        pageArea.addView(rendererCard)

        val resolutionRule = roundedCard(18)
        addReferenceSetting(resolutionRule, "Resolution Rule",
            "Choose how the game window resolution is calculated",
            "Selected: Percentage", false, "⌄") {
            showRendererChoiceDialog("Resolution Rule", listOf("Percentage", "Absolute", "Device default"))
        }
        pageArea.addView(resolutionRule)

        val scaleCard = roundedCard(18)
        val scaleBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(12), dp(18), dp(12))
        }
        scaleBox.addView(label("Resolution Scale", 15f, true))
        scaleBox.addView(label("Lower values improve performance; higher values improve quality. Adjust according to your needs", 12f))
        val percent = label("100%  ‹   ›", 13f, false).apply {
            setTextColor(accent)
            gravity = Gravity.CENTER
            setPadding(dp(16), 0, dp(8), 0)
        }
        val scaleRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val seek = android.widget.SeekBar(this).apply {
            max = 200
            progress = 100
            layoutParams = LinearLayout.LayoutParams(0, dp(50), 1f)
            setPadding(0, 0, dp(8), 0)
            setOnSeekBarChangeListener(object : android.widget.SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(sb: android.widget.SeekBar?, progress: Int, fromUser: Boolean) {
                    val shown = progress.coerceAtLeast(10)
                    percent.text = "${shown}%  ‹   ›"
                }
                override fun onStartTrackingTouch(sb: android.widget.SeekBar?) {}
                override fun onStopTrackingTouch(sb: android.widget.SeekBar?) {}
            })
        }
        scaleRow.addView(seek)
        scaleRow.addView(percent, LinearLayout.LayoutParams(dp(112), dp(48)))
        scaleBox.addView(scaleRow)
        scaleCard.addView(scaleBox)
        pageArea.addView(scaleCard)

        val fullCard = roundedCard(18)
        val fullBox = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(18), dp(10), dp(18), dp(10))
        }
        val fullText = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        fullText.addView(label("Game Fullscreen", 15f, true))
        fullText.addView(label("Enable fullscreen mode, ignoring safe areas like notches and punch-holes.", 12f))
        fullBox.addView(fullText, LinearLayout.LayoutParams(0, -2, 1f))
        val fullscreen = android.widget.Switch(this).apply {
            text = ""
            isChecked = true
            contentDescription = "Game Fullscreen"
        }
        fullBox.addView(fullscreen, LinearLayout.LayoutParams(dp(76), dp(52)))
        fullCard.addView(fullBox)
        pageArea.addView(fullCard)
    }

    private fun roundedCard(radius: Int): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        background = android.graphics.drawable.GradientDrawable().apply {
            setColor(Color.rgb(250, 250, 250))
            cornerRadius = dp(radius).toFloat()
            setStroke(dp(1), Color.rgb(232, 233, 235))
        }
        elevation = dp(1).toFloat()
        layoutParams = LinearLayout.LayoutParams(-1, -2).apply {
            setMargins(dp(6), dp(6), 0, dp(6))
        }
    }

    private fun addReferenceSetting(card: LinearLayout, name: String, description: String,
        selected: String, showDownload: Boolean, trailing: String, onClick: () -> Unit) {
        val row = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), dp(10), dp(10), dp(10))
        }
        row.setOnClickListener { onClick() }
        row.addView(label(name, 15f, true))
        if (description.isNotBlank()) row.addView(label(description, 12f))
        val bottom = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        bottom.addView(label(selected, 12.5f), LinearLayout.LayoutParams(0, dp(42), 1f))
        val action = button(trailing)
        action.textSize = if (showDownload) 20f else 18f
        action.setOnClickListener { onClick() }
        bottom.addView(action, LinearLayout.LayoutParams(dp(56), dp(42)))
        row.addView(bottom)
        card.addView(row)
        if (name != "Graphics API") {
            val divider = TextView(this).apply { setBackgroundColor(Color.rgb(225, 226, 228)) }
            card.addView(divider, LinearLayout.LayoutParams(-1, dp(1)))
        }
    }

    private fun showRendererChoiceDialog(titleText: String, options: List<String>) {
        val current = when (titleText) {
            "Global Renderer" -> "Krypton Wrapper"
            "Vulkan Driver" -> "Turnip"
            "Graphics API" -> "Only set to OpenGL on First launch"
            else -> "Percentage"
        }
        android.app.AlertDialog.Builder(this)
            .setTitle(titleText)
            .setSingleChoiceItems(options.toTypedArray(), options.indexOf(current).coerceAtLeast(0)) { dialog, which ->
                android.widget.Toast.makeText(this, "Selected: ${options[which]}", android.widget.Toast.LENGTH_SHORT).show()
                dialog.dismiss()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
'''


def replace_method(source: str) -> str:
    pattern = re.compile(r"    private fun rendererPage\(\) \{[\s\S]*?\n    \}\n\n    private fun javaPage\(\)", re.M)
    if not pattern.search(source):
        raise SystemExit("[step339] rendererPage/javaPage boundary not found")
    return pattern.sub(RENDERER_METHOD + "\n    private fun javaPage()", source, count=1)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step339] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    if MARKER not in source:
        source = replace_method(source)
    source = source.replace('        title.text = "Droid Launcher  ·  $page"',
                            '        title.text = if (page == "Renderer") "Settings · Renderer" else "Droid Launcher  ·  $page"', 1)
    ui.write_text(source, encoding="utf-8")
    print("[step339] Settings · Renderer reference GUI installed from 2.jpeg")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
