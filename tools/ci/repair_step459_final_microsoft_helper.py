#!/usr/bin/env python3
"""Step 459: restore the Microsoft browser helper at the absolute final source boundary.

The generated launcher UI is rewritten by several late CI stages. This small,
idempotent repair runs after those mutations and guarantees that both Microsoft
browser/cosmetic picker calls have exactly one real implementation.
"""
from pathlib import Path
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
BROWSER_SIGNATURE = "    private fun openMicrosoftLoginWebsite()"
PICKER_SIGNATURE = "    private fun openCosmeticImagePicker(requestCode: Int)"
ANCHOR = "    private fun showMicrosoftSignInPage()"

HELPER = '''    private fun openMicrosoftLoginWebsite() {
        val configured = getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .getString("microsoft_login_url", "")?.trim().orEmpty()
        val url = configured.ifBlank { "https://login.live.com/" }
        try {
            startActivity(
                android.content.Intent(
                    android.content.Intent.ACTION_VIEW,
                    android.net.Uri.parse(url)
                )
            )
            android.widget.Toast.makeText(
                this,
                "Microsoft sign-in opened in your browser.",
                android.widget.Toast.LENGTH_SHORT
            ).show()
        } catch (_: Throwable) {
            android.widget.Toast.makeText(
                this,
                "Unable to open Microsoft sign-in.",
                android.widget.Toast.LENGTH_LONG
            ).show()
        }
    }

    private fun openCosmeticImagePicker(requestCode: Int) {
        require(requestCode == 3371 || requestCode == 3372)
        val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "image/*"
            addFlags(
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or
                    android.content.Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
            )
        }
        try {
            startActivityForResult(intent, requestCode)
        } catch (_: Throwable) {
            android.widget.Toast.makeText(
                this,
                "No image picker is available on this device.",
                android.widget.Toast.LENGTH_LONG
            ).show()
        }
    }

'''


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step459] expected exactly one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise ValueError(signature)
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit("[step459] helper opening brace missing")
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ""
        n2 = source[i + 2] if i + 2 < len(source) else ""
        if state == "line":
            if c == "\n":
                state = "code"
            i += 1
            continue
        if state == "block":
            if c == "*" and n == "/":
                state = "code"
                i += 2
            else:
                i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"':
                state = "code"
                i += 3
            else:
                i += 1
            continue
        if state == "string":
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                state = "code"
            i += 1
            continue
        if c == "/" and n == "/":
            state = "line"
            i += 2
            continue
        if c == "/" and n == "*":
            state = "block"
            i += 2
            continue
        if c == '"' and n == '"' and n2 == '"':
            state = "triple"
            i += 3
            continue
        if c == '"':
            state = "string"
            i += 1
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
        i += 1
    raise SystemExit("[step459] unterminated Microsoft browser helper")


def remove_all_helpers(source: str) -> str:
    # Some legacy generators emitted these declarations without indentation.
    # Normalize the declaration line first so every duplicate is removed.
    for signature in (BROWSER_SIGNATURE, PICKER_SIGNATURE):
        declaration = signature.strip()
        source = re.sub(
            r"(?m)^[ \t]*" + re.escape(declaration) + r"(?=\s*\{)",
            signature,
            source,
        )
        while signature in source:
            start, end = method_span(source, signature)
            source = source[:start] + source[end:]
    return source


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")
    source = remove_all_helpers(source)

    anchor = source.find(ANCHOR)
    if anchor < 0:
        raise SystemExit("[step459] Microsoft sign-in page anchor missing")
    source = source[:anchor] + HELPER + source[anchor:]
    ui.write_text(source, encoding="utf-8")

    verify = ui.read_text(encoding="utf-8")
    if verify.count(BROWSER_SIGNATURE) != 1:
        raise SystemExit(f"[step459] browser helper declaration count is {verify.count(BROWSER_SIGNATURE)}, expected 1")
    if verify.count(PICKER_SIGNATURE) != 1:
        raise SystemExit(f"[step459] cosmetic picker declaration count is {verify.count(PICKER_SIGNATURE)}, expected 1")
    if "android.content.Intent.ACTION_VIEW" not in verify:
        raise SystemExit("[step459] browser helper ACTION_VIEW contract missing")
    if "android.content.Intent.ACTION_OPEN_DOCUMENT" not in verify:
        raise SystemExit("[step459] cosmetic picker ACTION_OPEN_DOCUMENT contract missing")
    if 'https://login.live.com/' not in verify:
        raise SystemExit("[step459] default Microsoft login URL missing")
    if "openMicrosoftLoginWebsite()" not in verify:
        raise SystemExit("[step459] browser helper implementation missing")
    if "openCosmeticImagePicker(requestCode: Int)" not in verify:
        raise SystemExit("[step459] cosmetic picker implementation missing")
    print("[step459] final Microsoft browser and cosmetic picker helpers restored exactly once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
