#!/usr/bin/env python3
"""Step 337: Microsoft account page plus real device image pickers."""
from pathlib import Path
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step337] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step337] method not found: {signature}")
    brace = source.find("{", start)
    depth = 0
    quote = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                quote = False
            continue
        if ch == '"':
            quote = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit("[step337] unterminated Kotlin method")


PAGE = r'''    private fun showMicrosoftAccountInfo() { showMicrosoftSignInPage() }

    private fun openMicrosoftLoginWebsite() {
        val configured = getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .getString("microsoft_login_url", "")?.trim().orEmpty()
        val url = configured.ifBlank { "https://login.live.com/" }
        try {
            startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url)))
            android.widget.Toast.makeText(this, "Microsoft sign-in opened in your browser.", android.widget.Toast.LENGTH_SHORT).show()
        } catch (_: Throwable) {
            android.widget.Toast.makeText(this, "Unable to open Microsoft sign-in.", android.widget.Toast.LENGTH_LONG).show()
        }
    }

    private fun openCosmeticImagePicker(requestCode: Int) {
        require(requestCode == 3371 || requestCode == 3372)
        val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "image/*"
            addFlags(android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or android.content.Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
        }
        try { startActivityForResult(intent, requestCode) }
        catch (_: Throwable) { android.widget.Toast.makeText(this, "No image picker is available on this device.", android.widget.Toast.LENGTH_LONG).show() }
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
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        header.addView(label("Droid Launcher", 20f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        header.addView(button("⌂", true).apply {
            contentDescription = "Home - return to Droid Launcher"
            setOnClickListener { showPage("Game") }
        }, LinearLayout.LayoutParams(dp(58), dp(54)))
        root.addView(header, LinearLayout.LayoutParams(-1, dp(60)))
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; gravity = Gravity.CENTER }
        val signIn = button("Sign in with Microsoft", true).apply {
            contentDescription = "Sign in with Microsoft"
            setOnClickListener { openMicrosoftLoginWebsite() }
        }
        content.addView(signIn, LinearLayout.LayoutParams(-1, dp(72)))
        val actions = LinearLayout(this).apply { gravity = Gravity.CENTER }
        actions.addView(button("Upload\nskin").apply {
            contentDescription = "Choose Minecraft skin image"
            setOnClickListener { openCosmeticImagePicker(3371) }
        }, LinearLayout.LayoutParams(dp(150), dp(150)).apply { rightMargin = dp(12) })
        actions.addView(button("Upload\ncape").apply {
            contentDescription = "Choose Minecraft cape image"
            setOnClickListener { openCosmeticImagePicker(3372) }
        }, LinearLayout.LayoutParams(dp(150), dp(150)).apply { leftMargin = dp(12) })
        content.addView(actions, LinearLayout.LayoutParams(-1, dp(170)))
        content.addView(label("Choose a skin or cape image from your device. Microsoft authentication opens only after the sign-in button is pressed.", 12f, false))
        root.addView(content, LinearLayout.LayoutParams(-1, 0, 1f))
        pageArea.addView(root, LinearLayout.LayoutParams(-1, -1))
    }
'''


def insert_before_class_end(source: str, block: str) -> str:
    pos = source.rfind('\n}')
    if pos < 0:
        raise SystemExit('[step337] class closing brace not found')
    return source[:pos] + '\n\n' + block + source[pos:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_ui(root)
    source = path.read_text(encoding="utf-8")

    # Modern generated variants may no longer contain the old account-info helper.
    # In that case insert the complete real Microsoft page directly before the
    # activity class closing brace. This makes the repair independent of an older
    # generator shape.
    if "private fun showMicrosoftSignInPage()" not in source:
        old = "    private fun showMicrosoftAccountInfo()"
        if old in source:
            start, end = method_span(source, old)
            source = source[:start] + PAGE + source[end:]
        else:
            source = insert_before_class_end(source, PAGE)

    source = source.replace('ms.setOnClickListener { showMicrosoftAccountInfo() }', 'ms.setOnClickListener { showMicrosoftSignInPage() }', 1)
    path.write_text(source, encoding="utf-8")

    verify = path.read_text(encoding="utf-8")
    required = (
        "private fun showMicrosoftSignInPage()",
        "private fun openMicrosoftLoginWebsite()",
        "private fun openCosmeticImagePicker(requestCode: Int)",
        "android.content.Intent.ACTION_VIEW",
        "android.content.Intent.ACTION_OPEN_DOCUMENT",
        "https://login.live.com/",
        "openCosmeticImagePicker(3371)",
        "openCosmeticImagePicker(3372)",
    )
    missing = [x for x in required if x not in verify]
    if missing:
        raise SystemExit("[step337] missing contract(s): " + ", ".join(missing))
    if 'ms.setOnClickListener { showMicrosoftAccountInfo() }' in verify:
        raise SystemExit("[step337] obsolete Microsoft entry remains")
    if 'Skin picker is ready for the next image-selection step.' in verify or 'Cape picker is ready for the next image-selection step.' in verify:
        raise SystemExit("[step337] obsolete fake cosmetic picker toast remains")
    print("[step337] real Android skin/cape image picker wiring applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
