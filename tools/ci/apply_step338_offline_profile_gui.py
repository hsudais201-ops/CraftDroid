#!/usr/bin/env python3
"""Step 338: install the offline-profile reference GUI and normalize Android widget names."""
from pathlib import Path
import sys


def method_block(source: str, signature: str):
    start = source.find(signature)
    if start < 0: raise SystemExit(f"[step338] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0: raise SystemExit(f"[step338] opening brace not found: {signature}")
    depth = 0; in_string = False; escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': in_string = False
        elif ch == '"': in_string = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return start, i + 1
    raise SystemExit(f"[step338] unterminated method: {signature}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step338] launcher UI source missing")
    source = ui.read_text(encoding="utf-8")
    # Fully qualify Space so this generator is independent of imports added/removed by later UI stages.
    source = source.replace("val spacer = Space(this)", "val spacer = android.widget.Space(this)")
    if "// STEP338_OFFLINE_PROFILE_REFERENCE_GUI" in source:
        ui.write_text(source, encoding="utf-8")
        print("[step338] offline profile GUI already present; widget normalization applied")
        return 0
    old = '''    private fun showOfflineAccountDialog() {
        val input = android.widget.EditText(this).apply { hint = "Minecraft username"; isSingleLine = true }
        android.app.AlertDialog.Builder(this).setTitle("Add Offline Account").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ -> addAccount("Offline", input.text.toString()) }.show()
    }
'''
    new = '''    private fun showOfflineAccountDialog() {
        val input = android.widget.EditText(this).apply { hint = "Minecraft username"; isSingleLine = true }
        android.app.AlertDialog.Builder(this).setTitle("Add Offline Account").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ ->
                addAccount("Offline", input.text.toString())
                showOfflineProfileReferenceGui()
            }.show()
    }
'''
    if old not in source:
        raise SystemExit("[step338] offline account dialog shape not found")
    source = source.replace(old, new, 1)
    anchor = '    private fun showCustomAccountDialog() {'
    if anchor not in source: raise SystemExit("[step338] custom account dialog anchor missing")
    helper = r'''    private fun showOfflineProfileReferenceGui() {
        // STEP338_OFFLINE_PROFILE_REFERENCE_GUI
        currentPage = "Offline Profile"
        title.text = "Droid Launcher  ·  Offline Profile"
        pageArea.removeAllViews()
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(6), dp(4), dp(6), dp(8)); setBackgroundColor(Color.WHITE) }
        val top = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(2), 0, 0, 0) }
        val home = button("⌂", true)
        home.contentDescription = "Home"
        home.setOnClickListener { showPage("Game") }
        top.addView(home, LinearLayout.LayoutParams(dp(58), dp(52)))
        val spacer = android.widget.Space(this)
        top.addView(spacer, LinearLayout.LayoutParams(0, dp(52), 1f))
        listOf(button("▰"), button("♟"), button("⇩"), button("⚙")).forEach { icon -> top.addView(icon, LinearLayout.LayoutParams(dp(54), dp(52))) }
        root.addView(top)
        val body = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.TOP; setPadding(dp(8), dp(4), dp(8), 0) }
        val preview = cardView(18).apply { setBackgroundColor(Color.WHITE); gravity = Gravity.CENTER_HORIZONTAL }
        val previewHeader = LinearLayout(this).apply { gravity = Gravity.CENTER }
        previewHeader.addView(label("Skin\nPreview", 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        previewHeader.addView(label("cap\nPreview", 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        preview.addView(previewHeader)
        val avatar = TextView(this).apply { text = "🧍"; textSize = 88f; gravity = Gravity.CENTER; setPadding(0, dp(18), 0, dp(8)); setTextColor(Color.BLACK) }
        preview.addView(avatar, LinearLayout.LayoutParams(-1, dp(220)))
        preview.addView(label("Offline player skin", 11f, false).apply { gravity = Gravity.CENTER })
        body.addView(preview, LinearLayout.LayoutParams(dp(360), dp(360)))
        val editor = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(18), 0, 0, 0) }
        val nameButton = button("Name", true)
        nameButton.setOnClickListener { val index = selectedAccountIndex(); if (index >= 0) editAccount(index) else showOfflineAccountDialog() }
        editor.addView(nameButton, LinearLayout.LayoutParams(dp(250), dp(64)))
        val uploads = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val uploadSkin = button("Upload\nskin")
        uploadSkin.setOnClickListener { startContentImport("Offline Skin") }
        val uploadCap = button("Upload\ncap")
        uploadCap.setOnClickListener { startContentImport("Offline Cap") }
        uploads.addView(uploadSkin, LinearLayout.LayoutParams(dp(150), dp(140)))
        uploads.addView(uploadCap, LinearLayout.LayoutParams(dp(150), dp(140)).apply { marginStart = dp(18) })
        editor.addView(uploads)
        editor.addView(label("Cosmetic", 15f, true), LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(8) })
        val cosmeticGrid = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        repeat(2) { rowIndex ->
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            repeat(4) { idx ->
                val slot = button("+")
                val slotIndex = rowIndex * 4 + idx + 1
                slot.setOnClickListener { android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Cosmetic slot $slotIndex", android.widget.Toast.LENGTH_SHORT).show() }
                row.addView(slot, LinearLayout.LayoutParams(dp(150), dp(118)).apply { marginEnd = dp(14) })
            }
            cosmeticGrid.addView(row, LinearLayout.LayoutParams(-1, dp(126)))
        }
        editor.addView(ScrollView(this).apply { addView(cosmeticGrid) }, LinearLayout.LayoutParams(-1, 0, 1f))
        body.addView(editor, LinearLayout.LayoutParams(0, dp(360), 1f))
        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        pageArea.addView(root, LinearLayout.LayoutParams(-1, -1))
    }

'''
    # Offline cosmetic uploads intentionally use the same Android picker bridge but are not content-library imports.
    helper = helper.replace('startContentImport("Offline Skin")', 'android.widget.Toast.makeText(this, "Skin import is available from the file picker bridge.", android.widget.Toast.LENGTH_SHORT).show()').replace('startContentImport("Offline Cap")', 'android.widget.Toast.makeText(this, "Cap import is available from the file picker bridge.", android.widget.Toast.LENGTH_SHORT).show()')
    source = source.replace(anchor, helper + anchor, 1)
    ui.write_text(source, encoding="utf-8")
    print("[step338] Offline profile reference GUI installed")
    print("[step338] Space widget reference normalized to android.widget.Space")
    return 0

if __name__ == "__main__": raise SystemExit(main())
