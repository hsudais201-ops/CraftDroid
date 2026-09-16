#!/usr/bin/env python3
"""Step 338: add the offline-profile cosmetic GUI from the supplied reference image.

The screen keeps the existing local/offline account data while presenting a matching
wide, minimal Minecraft-style editor layout: Home navigation, utility icons, skin/cap
preview area, profile name, upload actions, and cosmetic slots.
"""
from pathlib import Path
import sys


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step338] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step338] opening brace not found: {signature}")
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit(f"[step338] unterminated method: {signature}")


def replace_method(source: str, signature: str, replacement: str) -> str:
    start, end = method_block(source, signature)
    return source[:start] + replacement + source[end:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step338] launcher UI source missing")
    source = ui.read_text(encoding="utf-8")
    if "// STEP338_OFFLINE_PROFILE_REFERENCE_GUI" in source:
        print("[step338] offline profile GUI already present")
        return 0

    old_add = '''    private fun showOfflineAccountDialog() {
        val input = android.widget.EditText(this).apply { hint = "Minecraft username"; singleLine = true }
        android.app.AlertDialog.Builder(this).setTitle("Add Offline Account").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ -> addAccount("Offline", input.text.toString()) }.show()
    }
'''
    new_add = '''    private fun showOfflineAccountDialog() {
        val input = android.widget.EditText(this).apply { hint = "Minecraft username"; singleLine = true }
        android.app.AlertDialog.Builder(this).setTitle("Add Offline Account").setView(input)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Add") { _, _ ->
                addAccount("Offline", input.text.toString())
                showOfflineProfileReferenceGui()
            }.show()
    }
'''
    if old_add not in source:
        raise SystemExit("[step338] offline account dialog shape not found")
    source = source.replace(old_add, new_add, 1)

    marker = '    private fun showCustomAccountDialog() {'
    if marker not in source:
        raise SystemExit("[step338] custom account dialog anchor missing")

    helper = r'''    private fun showOfflineProfileReferenceGui() {
        // STEP338_OFFLINE_PROFILE_REFERENCE_GUI
        currentPage = "Offline Profile"
        title.text = "Droid Launcher  ·  Offline Profile"
        pageArea.removeAllViews()

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(6), dp(4), dp(6), dp(8))
            setBackgroundColor(Color.WHITE)
        }

        val top = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(2), 0, 0, 0)
        }
        val home = button("⌂", true)
        home.contentDescription = "Home"
        home.setOnClickListener { showPage("Game") }
        top.addView(home, LinearLayout.LayoutParams(dp(58), dp(52)))
        val spacer = Space(this)
        top.addView(spacer, LinearLayout.LayoutParams(0, dp(52), 1f))
        listOf(
            button("▰"),
            button("♟"),
            button("⇩"),
            button("⚙"),
        ).forEach { icon -> top.addView(icon, LinearLayout.LayoutParams(dp(54), dp(52))) }
        root.addView(top)

        val body = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.TOP
            setPadding(dp(8), dp(4), dp(8), 0)
        }

        val preview = cardView(18).apply {
            setBackgroundColor(Color.WHITE)
            gravity = Gravity.CENTER_HORIZONTAL
        }
        val previewHeader = LinearLayout(this).apply { gravity = Gravity.CENTER }
        previewHeader.addView(label("Skin\nPreview", 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        previewHeader.addView(label("cap\nPreview", 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        preview.addView(previewHeader)

        val avatar = TextView(this).apply {
            text = "🧍"
            textSize = 88f
            gravity = Gravity.CENTER
            setPadding(0, dp(18), 0, dp(8))
            setTextColor(Color.BLACK)
        }
        preview.addView(avatar, LinearLayout.LayoutParams(-1, dp(220)))
        val hint = label("Offline player skin", 11f, false)
        hint.gravity = Gravity.CENTER
        preview.addView(hint)
        body.addView(preview, LinearLayout.LayoutParams(dp(360), dp(360)))

        val editor = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(18), 0, 0, 0)
        }
        val nameButton = button("Name", true)
        nameButton.setOnClickListener {
            val index = selectedAccountIndex()
            if (index >= 0) editAccount(index) else showOfflineAccountDialog()
        }
        editor.addView(nameButton, LinearLayout.LayoutParams(dp(250), dp(64)))

        val uploads = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val uploadSkin = button("Upload\nskin")
        uploadSkin.setOnClickListener {
            android.widget.Toast.makeText(this, "Skin import can be connected to the Android file picker.", android.widget.Toast.LENGTH_SHORT).show()
        }
        val uploadCap = button("Upload\ncap")
        uploadCap.setOnClickListener {
            android.widget.Toast.makeText(this, "Cap import can be connected to the Android file picker.", android.widget.Toast.LENGTH_SHORT).show()
        }
        uploads.addView(uploadSkin, LinearLayout.LayoutParams(dp(150), dp(140)))
        uploads.addView(uploadCap, LinearLayout.LayoutParams(dp(150), dp(140)).apply { marginStart = dp(18) })
        editor.addView(uploads)

        editor.addView(label("Cosmetic", 15f, true), LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(8) })
        val cosmeticGrid = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        repeat(2) { rowIndex ->
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            repeat(4) {
                val slot = button("+")
                slot.setOnClickListener {
                    android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Cosmetic slot ${rowIndex * 4 + it + 1}", android.widget.Toast.LENGTH_SHORT).show()
                }
                row.addView(slot, LinearLayout.LayoutParams(150.dpCompat(), 118.dpCompat()).apply { marginEnd = dp(14) })
            }
            cosmeticGrid.addView(row, LinearLayout.LayoutParams(-1, dp(126)))
        }
        editor.addView(ScrollView(this).apply { addView(cosmeticGrid) }, LinearLayout.LayoutParams(-1, 0, 1f))
        body.addView(editor, LinearLayout.LayoutParams(0, 0, 1f).apply { height = dp(360) })

        root.addView(body, LinearLayout.LayoutParams(-1, 0, 1f))
        pageArea.addView(root, LinearLayout.LayoutParams(-1, -1))
    }

    private fun Int.dpCompat(): Int = dp(this)

'''
    source = source.replace(marker, helper + marker, 1)

    ui.write_text(source, encoding="utf-8")
    print("[step338] Offline profile reference GUI installed")
    print("[step338] Offline Add action now opens the reference-style profile screen")
    print("[step338] Top-left Home action returns to Droid Launcher")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
