#!/usr/bin/env python3
"""Step 347: replace Version / Instances with the supplied screenshot's black/white layout."""
from pathlib import Path
import sys

MARKER = "// STEP347_VERSION_INSTANCE_PIXEL_LAYOUT"

def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0: raise SystemExit(f"[step347] method not found: {signature}")
    brace = source.find("{", start)
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
            continue
        if ch == '"': in_string = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return start, i + 1
    raise SystemExit("[step347] unterminated method")

PAGE = r'''    private fun showVersionInstancesPage() {
        // STEP347_VERSION_INSTANCE_PIXEL_LAYOUT
        title.visibility = android.view.View.GONE
        pageArea.removeAllViews()

        fun blackText(v: android.widget.TextView, size: Float) {
            v.setTextColor(android.graphics.Color.BLACK)
            v.textSize = size
            v.setAllCaps(false)
            v.setBackgroundColor(android.graphics.Color.WHITE)
        }
        fun dashedBorderPanel(textValue: String, heightDp: Int, click: (() -> Unit)? = null): android.widget.FrameLayout {
            val box = android.widget.FrameLayout(this)
            val border = object : android.view.View(this) {
                override fun onDraw(canvas: android.graphics.Canvas) {
                    super.onDraw(canvas)
                    val p = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
                        style = android.graphics.Paint.Style.STROKE
                        color = android.graphics.Color.BLACK
                        strokeWidth = dp(2).toFloat()
                        pathEffect = android.graphics.DashPathEffect(floatArrayOf(dp(9).toFloat(), dp(7).toFloat()), 0f)
                    }
                    canvas.drawRoundRect(android.graphics.RectF(dp(1).toFloat(), dp(1).toFloat(), width - dp(1).toFloat(), height - dp(1).toFloat()), dp(12).toFloat(), dp(12).toFloat(), p)
                }
            }.apply { setLayerType(android.view.View.LAYER_TYPE_SOFTWARE, null) }
            box.addView(border, android.widget.FrameLayout.LayoutParams(-1, -1))
            val label = android.widget.TextView(this).apply {
                text = textValue
                gravity = android.view.Gravity.CENTER
                setPadding(dp(8), 0, dp(8), 0)
                blackText(this, 15f)
                if (click != null) setOnClickListener { click.invoke() }
            }
            box.addView(label, android.widget.FrameLayout.LayoutParams(-1, -1).apply { leftMargin = dp(4); rightMargin = dp(4); topMargin = dp(4); bottomMargin = dp(4) })
            return box
        }
        fun dottedBox(widthDp: Int, heightDp: Int): android.view.View = object : android.view.View(this) {
            override fun onDraw(canvas: android.graphics.Canvas) {
                val p = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply {
                    style = android.graphics.Paint.Style.STROKE
                    color = android.graphics.Color.BLACK
                    strokeWidth = dp(2).toFloat()
                    pathEffect = android.graphics.DashPathEffect(floatArrayOf(dp(3).toFloat(), dp(4).toFloat()), 0f)
                }
                canvas.drawRoundRect(android.graphics.RectF(dp(2).toFloat(), dp(2).toFloat(), width - dp(2).toFloat(), height - dp(2).toFloat()), dp(8).toFloat(), dp(8).toFloat(), p)
            }
        }.apply { setLayerType(android.view.View.LAYER_TYPE_SOFTWARE, null) }

        val top = android.widget.LinearLayout(this).apply {
            gravity = android.view.Gravity.CENTER_VERTICAL
            setPadding(dp(22), dp(2), dp(22), 0)
        }
        val home = android.widget.TextView(this).apply {
            text = "⌂"
            gravity = android.view.Gravity.CENTER
            blackText(this, 28f)
            contentDescription = "Home"
            setOnClickListener { title.visibility = android.view.View.VISIBLE; showPage("Game") }
        }
        top.addView(home, android.widget.LinearLayout.LayoutParams(dp(58), dp(56)))
        val spacer = android.view.View(this)
        top.addView(spacer, android.widget.LinearLayout.LayoutParams(0, 1, 1f))
        listOf("▰" to "Files", "♟" to "Accounts", "⇩" to "Downloads", "⚙" to "Settings").forEach { pair ->
            val icon = android.widget.TextView(this).apply {
                text = pair.first
                gravity = android.view.Gravity.CENTER
                blackText(this, 25f)
                contentDescription = pair.second
                setOnClickListener {
                    when (pair.second) {
                        "Settings" -> { title.visibility = android.view.View.VISIBLE; showPage("Renderer") }
                        "Accounts" -> { title.visibility = android.view.View.VISIBLE; showPage("Accounts") }
                        else -> android.widget.Toast.makeText(this@DroidLauncherUiActivity, pair.second, android.widget.Toast.LENGTH_SHORT).show()
                    }
                }
            }
            top.addView(icon, android.widget.LinearLayout.LayoutParams(dp(58), dp(56)))
        }
        pageArea.addView(top)

        val plusRow = android.widget.LinearLayout(this).apply { setPadding(dp(50), 0, 0, dp(8)) }
        val plus = android.widget.TextView(this).apply {
            text = "+"
            gravity = android.view.Gravity.CENTER
            blackText(this, 54f)
            contentDescription = "Add version"
            setOnClickListener { title.visibility = android.view.View.VISIBLE; libraryPage("Game") }
        }
        plusRow.addView(plus, android.widget.LinearLayout.LayoutParams(dp(90), dp(74)))
        pageArea.addView(plusRow)

        val contentRow = android.widget.LinearLayout(this).apply { orientation = android.widget.LinearLayout.HORIZONTAL; setPadding(dp(22), 0, dp(22), dp(10)) }
        val listFrame = android.widget.FrameLayout(this)
        fun addEntry(value: String, rowIndex: Int) {
            val row = android.widget.FrameLayout(this)
            row.setPadding(dp(18), dp(13), dp(18), dp(13))
            val left = dottedBox(142, 130)
            row.addView(left, android.widget.FrameLayout.LayoutParams(dp(148), dp(134)).apply { leftMargin = dp(16); topMargin = dp(12) })
            val field = android.widget.EditText(this).apply {
                setText(value)
                isSingleLine = true
                setTextColor(android.graphics.Color.BLACK)
                textSize = 14f
                setPadding(dp(16), 0, dp(16), 0)
                background = android.graphics.drawable.GradientDrawable().apply { setColor(android.graphics.Color.WHITE); setStroke(dp(2), android.graphics.Color.BLACK) }
                hint = if (rowIndex == 0) "Minecraft version" else "Instance name"
            }
            row.addView(field, android.widget.FrameLayout.LayoutParams(dp(660), dp(48)).apply { leftMargin = dp(235); topMargin = dp(54) })
            val trash = android.widget.TextView(this).apply {
                text = "⌫"
                gravity = android.view.Gravity.CENTER
                blackText(this, 23f)
                contentDescription = "Delete row"
                setOnClickListener { field.text.clear() }
            }
            row.addView(trash, android.widget.FrameLayout.LayoutParams(dp(54), dp(54)).apply { leftMargin = dp(935); topMargin = dp(25) })
            val folder = android.widget.TextView(this).apply {
                text = "▣"
                gravity = android.view.Gravity.CENTER
                blackText(this, 24f)
                contentDescription = "Open folder"
                setOnClickListener { android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Folder: ${field.text}", android.widget.Toast.LENGTH_SHORT).show() }
            }
            row.addView(folder, android.widget.FrameLayout.LayoutParams(dp(54), dp(54)).apply { leftMargin = dp(935); topMargin = dp(88) })
            if (rowIndex < 2) row.background = android.graphics.drawable.GradientDrawable().apply { setColor(android.graphics.Color.WHITE); setStroke(dp(1), android.graphics.Color.BLACK) }
            listFrame.addView(row, android.widget.FrameLayout.LayoutParams(-1, dp(190)).apply { topMargin = dp(rowIndex * 200) })
        }
        val listBorder = object : android.view.View(this) {
            override fun onDraw(canvas: android.graphics.Canvas) {
                val p = android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG).apply { style = android.graphics.Paint.Style.STROKE; color = android.graphics.Color.BLACK; strokeWidth = dp(2).toFloat(); pathEffect = android.graphics.DashPathEffect(floatArrayOf(dp(10).toFloat(), dp(8).toFloat()), 0f) }
                canvas.drawRoundRect(android.graphics.RectF(dp(1).toFloat(), dp(1).toFloat(), width-dp(1).toFloat(), height-dp(1).toFloat()), dp(14).toFloat(), dp(14).toFloat(), p)
            }
        }.apply { setLayerType(android.view.View.LAYER_TYPE_SOFTWARE, null) }
        listFrame.addView(listBorder, 0, android.widget.FrameLayout.LayoutParams(-1, dp(610)))
        addEntry(selectedMinecraftVersion(), 0)
        addEntry(selectedMinecraftProfile(), 1)
        addEntry("Survival", 2)
        contentRow.addView(listFrame, android.widget.LinearLayout.LayoutParams(0, dp(612), 1f))

        val rail = android.widget.LinearLayout(this).apply { orientation = android.widget.LinearLayout.VERTICAL; setPadding(dp(16), 0, 0, 0) }
        val back = dashedBorderPanel("back", 300) { title.visibility = android.view.View.VISIBLE; showPage("Game") }
        rail.addView(back, android.widget.LinearLayout.LayoutParams(dp(220), dp(302)))
        val select = dashedBorderPanel("Select", 92) {
            val cards = listFrame
            val fields = (0 until cards.childCount).mapNotNull { cards.getChildAt(it) as? android.widget.FrameLayout }.flatMap { f -> (0 until f.childCount).mapNotNull { f.getChildAt(it) as? android.widget.EditText } }
            fields.firstOrNull()?.text?.toString()?.takeIf { it.isNotBlank() }?.let { saveMinecraftVersion(it) }
            fields.drop(1).firstOrNull()?.text?.toString()?.takeIf { it.isNotBlank() }?.let { saveMinecraftProfile(it) }
            title.visibility = android.view.View.VISIBLE
            showPage("Game")
        }
        rail.addView(select, android.widget.LinearLayout.LayoutParams(dp(220), dp(92)).apply { topMargin = dp(16) })
        rail.addView(dashedBorderPanel("Create server", 54) { android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Create server", android.widget.Toast.LENGTH_SHORT).show() }, android.widget.LinearLayout.LayoutParams(dp(220), dp(54)).apply { topMargin = dp(12) })
        rail.addView(dashedBorderPanel("Coming soon", 92), android.widget.LinearLayout.LayoutParams(dp(220), dp(92)).apply { topMargin = dp(8) })
        contentRow.addView(rail, android.widget.LinearLayout.LayoutParams(dp(250), dp(612)))
        pageArea.addView(contentRow)
    }
'''

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step347] missing UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    start, end = method_block(s, '    private fun showVersionInstancesPage() {')
    s = s[:start] + PAGE + s[end:]
    if 'title.visibility = android.view.View.VISIBLE' not in s:
        s = s.replace('    private fun showPage(page: String) {', '    private fun showPage(page: String) {\n        title.visibility = android.view.View.VISIBLE', 1)
    s = s.replace('    // STEP346_VERSION_INSTANCE_REFERENCE_SCREEN\n', '')
    ui.write_text(s, encoding="utf-8")
    print("[step347] screenshot-matched Version / Instances layout installed")
    return 0

if __name__ == "__main__": raise SystemExit(main())
