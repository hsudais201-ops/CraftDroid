#!/usr/bin/env python3
"""Step 461: low-RAM heap hardening and real CraftDroid logo asset."""
from pathlib import Path
import re
import sys

UI_NAME = "DroidLauncherUiActivity.kt"
MANIFEST_REL = Path("app/src/main/AndroidManifest.xml")
LOGO_REL = Path("app/src/main/res/drawable/craftdroid_logo.xml")
MARKER = "// STEP461_REAL_LOGO_AND_MEMORY"


LOGO_XML = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#08111C"
        android:pathData="M12,0 L96,0 A12,12 0,0 1,108 12 L108,96 A12,12 0,0 1,96 108 L12,108 A12,12 0,0 1,0 96 L0,12 A12,12 0,0 1,12 0 Z" />
    <path
        android:fillColor="#17CD8F"
        android:pathData="M54,16 L86,34 L86,72 L54,90 L22,72 L22,34 Z" />
    <path
        android:fillColor="#0A111C"
        android:pathData="M31,39 L46,31 L46,66 L31,74 Z" />
    <path
        android:fillColor="#0A111C"
        android:pathData="M51,29 L68,38 L68,72 L51,81 Z" />
    <path
        android:fillColor="#2478D6"
        android:pathData="M78,35 L86,39 L86,69 L78,73 Z" />
    <path
        android:fillColor="#F2FFF9"
        android:pathData="M36,45 L42,42 L42,60 L36,63 Z" />
    <path
        android:fillColor="#F2FFF9"
        android:pathData="M56,39 L63,43 L63,60 L56,64 Z" />
</vector>
"""


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob(UI_NAME))
    if len(hits) != 1:
        raise SystemExit(f"[step461] expected exactly one {UI_NAME}, found {len(hits)}")
    return hits[0]


def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit("[step461] missing method: " + signature)
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit("[step461] missing opening brace: " + signature)
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
    raise SystemExit("[step461] unterminated method: " + signature)


def patch_logo_resource(root: Path) -> None:
    path = root / LOGO_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(LOGO_XML, encoding="utf-8")


def patch_manifest(root: Path) -> None:
    path = root / MANIFEST_REL
    if not path.is_file():
        raise SystemExit("[step461] AndroidManifest.xml missing")
    source = path.read_text(encoding="utf-8")
    app_match = re.search(r"<application\b[^>]*>", source)
    if not app_match:
        raise SystemExit("[step461] application element missing")
    tag = app_match.group(0)

    def replace_or_add(attr: str, value: str, tag_text: str) -> str:
        pattern = rf'\s+android:{re.escape(attr)}="[^"]*"'
        if re.search(pattern, tag_text):
            return re.sub(pattern, f' android:{attr}="{value}"', tag_text, count=1)
        return tag_text[:-1] + f' android:{attr}="{value}">'

    new_tag = replace_or_add("icon", "@drawable/craftdroid_logo", tag)
    new_tag = replace_or_add("roundIcon", "@drawable/craftdroid_logo", new_tag)
    source = source[:app_match.start()] + new_tag + source[app_match.end():]
    path.write_text(source, encoding="utf-8")


def patch_ui_logo(source: str) -> str:
    if MARKER in source:
        return source

    sig = '    private fun step460LogoBadge(labelText: String = "CD", size: Int = 46): TextView ='
    if sig not in source:
        raise SystemExit("[step461] Step460 logo helper not found")

    start, end = method_span(source, sig)
    replacement = r'''    // STEP461_REAL_LOGO_AND_MEMORY
    private fun step460LogoBadge(labelText: String = "CD", size: Int = 46): android.widget.ImageView =
        android.widget.ImageView(this).apply {
            setImageResource(R.drawable.craftdroid_logo)
            contentDescription = "CraftDroid logo"
            scaleType = android.widget.ImageView.ScaleType.CENTER_INSIDE
            setPadding(dp(5), dp(5), dp(5), dp(5))
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(14).toFloat()
                setColor(android.graphics.Color.argb(120, 8, 17, 28))
                setStroke(dp(1), android.graphics.Color.argb(120, 92, 244, 190))
            }
            elevation = if (step376LowRam) dp(1).toFloat() else dp(5).toFloat()
            minimumWidth = 0
            minimumHeight = 0
            layoutParams = LinearLayout.LayoutParams(dp(size), dp(size))
        }
'''
    source = source[:start] + replacement + source[end:]

    # Trim a little more UI overhead on low-memory devices.
    source = source.replace(
        '            setStroke(dp(1), android.graphics.Color.argb(strokeAlpha, 92, 244, 190))',
        '            setStroke(dp(1), android.graphics.Color.argb(if (step376LowRam) 45 else strokeAlpha, 92, 244, 190))',
        1,
    )
    return source


def validate(root: Path, source: str) -> None:
    logo = root / LOGO_REL
    manifest = root / MANIFEST_REL
    if not logo.is_file() or LOGO_XML.strip() != logo.read_text(encoding="utf-8").strip():
        raise SystemExit("[step461] real CraftDroid vector logo is missing or modified")
    mt = manifest.read_text(encoding="utf-8")
    for needle in ('android:icon="@drawable/craftdroid_logo"', 'android:roundIcon="@drawable/craftdroid_logo"'):
        if needle not in mt:
            raise SystemExit("[step461] manifest logo binding missing: " + needle)
    for needle in (
        MARKER,
        "R.drawable.craftdroid_logo",
        'contentDescription = "CraftDroid logo"',
        "step376LowRam",
    ):
        if needle not in source:
            raise SystemExit("[step461] UI logo contract missing: " + needle)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")

    patch_logo_resource(root)
    patch_manifest(root)
    source = patch_ui_logo(source)

    validate(root, source)
    ui.write_text(source, encoding="utf-8")
    print("[step461] real CraftDroid vector logo installed as APK icon and page logo")
    print("[step461] low-RAM logo/elevation styling is reduced without removing the branded asset")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
