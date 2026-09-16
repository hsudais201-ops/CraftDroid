#!/usr/bin/env python3
"""Step 337: add the Microsoft sign-in reference GUI and explicit browser-login action.

The launcher shows the account UI first. Tapping its Microsoft option opens this
custom in-launcher page; only the page's "Sign in with Microsoft" button launches
the real Microsoft login website. The top-right home button returns to Droid Launcher.
"""
from pathlib import Path
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step337] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step337] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step337] opening brace not found: {signature}")
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
    raise SystemExit(f"[step337] unterminated method: {signature}")


def replace_method(source: str, signature: str, replacement: str) -> str:
    start, end = method_block(source, signature)
    return source[:start] + replacement + source[end:]


MICROSOFT_PAGE = r'''    private fun showMicrosoftAccountInfo() {
        showMicrosoftSignInPage()
    }

    private fun microsoftDashedPanel(titleText: String, heightDp: Int = 150): LinearLayout {
        val panel = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = android.graphics.drawable.GradientDrawable().apply {
                shape = android.graphics.drawable.GradientDrawable.RECTANGLE
                cornerRadius = dp(14).toFloat()
                setColor(Color.WHITE)
                setStroke(dp(2), Color.DKGRAY, dp(7).toFloat(), dp(5).toFloat())
            }
        }
        panel.addView(label(titleText, 17f, true))
        panel.addView(label("+", 54f, true), LinearLayout.LayoutParams(-1, 0, 1f))
        panel.minimumHeight = dp(heightDp)
        return panel
    }

    private fun openMicrosoftLoginWebsite() {
        val configured = getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .getString("microsoft_login_url", "")?.trim().orEmpty()
        val url = configured.ifBlank { "https://login.live.com/" }
        try {
            val intent = android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url))
            startActivity(intent)
            android.widget.Toast.makeText(this, "Microsoft sign-in opened in your browser.", android.widget.Toast.LENGTH_SHORT).show()
        } catch (_: Throwable) {
            android.widget.Toast.makeText(this, "Unable to open Microsoft sign-in.", android.widget.Toast.LENGTH_LONG).show()
        }
    }

    private fun showMicrosoftSignInPage() {
        currentPage = "Microsoft Sign In"
        title.text = "Microsoft Sign In"
        pageArea.removeAllViews()

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.WHITE)
            setPadding(dp(10), dp(6), dp(10), dp(10))
        }

        val header = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(4), dp(2), dp(4), dp(4))
        }
        header.addView(label("Droid Launcher", 20f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        val home = button("⌂", true).apply {
            contentDescription = "Home - return to Droid Launcher"
            setOnClickListener { showPage("Game") }
        }
        header.addView(home, LinearLayout.LayoutParams(dp(58), dp(54)))
        root.addView(header, LinearLayout.LayoutParams(-1, dp(60)))

        val content = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.TOP }

        val preview = cardView(16).apply {
            setBackgroundColor(Color.WHITE)
            setPadding(dp(12), dp(10), dp(12), dp(10))
        }
        val previewRow = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER }
        val skin = microsoftDashedPanel("Skin\nPreview", 280)
        skin.addView(label("Minecraft Skin", 12f, false))
        previewRow.addView(skin, LinearLayout.LayoutParams(0, dp(330), 1f))
        val cap = microsoftDashedPanel("cap\nPreview", 150)
        cap.addView(label("Cape", 12f, false))
        previewRow.addView(cap, LinearLayout.LayoutParams(0, dp(330), 1f).apply { leftMargin = dp(10) })
        preview.addView(previewRow, LinearLayout.LayoutParams(-1, 0, 1f))
        content.addView(preview, LinearLayout.LayoutParams(dp(390), -1))

        val main = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14), 0, 0, 0)
        }

        val actions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val signIn = button("Sign in with Microsoft", true).apply {
            contentDescription = "Sign in with Microsoft"
            setOnClickListener { openMicrosoftLoginWebsite() }
        }
        actions.addView(signIn, LinearLayout.LayoutParams(0, dp(72), 1f))
        val uploadSkin = button("Upload\nskin")
        uploadSkin.setOnClickListener {
            android.widget.Toast.makeText(this, "Skin picker is ready for the next image-selection step.", android.widget.Toast.LENGTH_SHORT).show()
        }
        actions.addView(uploadSkin, LinearLayout.LayoutParams(dp(150), dp(150)).apply { leftMargin = dp(12) })
        val uploadCap = button("Upload\ncap")
        uploadCap.setOnClickListener {
            android.widget.Toast.makeText(this, "Cape picker is ready for the next image-selection step.", android.widget.Toast.LENGTH_SHORT).show()
        }
        actions.addView(uploadCap, LinearLayout.LayoutParams(dp(150), dp(150)).apply { leftMargin = dp(12) })
        main.addView(actions, LinearLayout.LayoutParams(-1, dp(170)))

        val grid = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        repeat(2) {
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER }
            repeat(4) {
                val add = microsoftDashedPanel("+", 150)
                row.addView(add, LinearLayout.LayoutParams(0, dp(150), 1f).apply {
                    leftMargin = dp(6); rightMargin = dp(6); bottomMargin = dp(10)
                })
            }
            grid.addView(row, LinearLayout.LayoutParams(-1, dp(160)))
        }
        main.addView(grid, LinearLayout.LayoutParams(-1, 0, 1f))
        main.addView(label("Microsoft authentication opens only after the button above is pressed.", 12f, false))

        content.addView(main, LinearLayout.LayoutParams(0, -1, 1f))
        root.addView(content, LinearLayout.LayoutParams(-1, 0, 1f))
        pageArea.addView(root, LinearLayout.LayoutParams(-1, -1))
    }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_ui(root)
    source = path.read_text(encoding="utf-8")

    if "private fun showMicrosoftSignInPage()" not in source:
        if "private fun showMicrosoftAccountInfo()" not in source:
            raise SystemExit("[step337] existing Microsoft account entry point is missing")
        source = replace_method(source, "    private fun showMicrosoftAccountInfo()", MICROSOFT_PAGE)

    source = source.replace('ms.setOnClickListener { showMicrosoftAccountInfo() }', 'ms.setOnClickListener { showMicrosoftSignInPage() }', 1)
    path.write_text(source, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    required = (
        "private fun showMicrosoftSignInPage()",
        "Sign in with Microsoft",
        "private fun openMicrosoftLoginWebsite()",
        "android.content.Intent.ACTION_VIEW",
        "https://login.live.com/",
        'contentDescription = "Home - return to Droid Launcher"',
        'setOnClickListener { showPage("Game") }',
        "Skin\\nPreview",
        "Upload\\nskin",
        "Upload\\ncap",
    )
    missing = [x for x in required if x not in verify]
    if missing:
        raise SystemExit("[step337] missing GUI contract(s): " + ", ".join(missing))
    if 'ms.setOnClickListener { showMicrosoftAccountInfo() }' in verify:
        raise SystemExit("[step337] Microsoft entry still points at the obsolete placeholder")

    print("[step337] Microsoft reference GUI applied")
    print("[step337] top-right Home button returns to Droid Launcher")
    print("[step337] Microsoft website opens only from the in-app sign-in button")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
