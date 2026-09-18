#!/usr/bin/env python3
"""Step 391: restore the real content picker after the final reference UI rewrite.

The reference-driven UI intentionally replaces the visible shell late in generation,
so the pre-existing Step 342 picker must be merged into the single Microsoft/cosmetic
ActivityResult callback rather than added as a second callback.
"""
from pathlib import Path
import re
import sys

UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")
MARKER = "// STEP391_FINAL_CONTENT_PICKER"


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step391] expected exactly one UI source, found {len(hits)}")
    return hits[0]


def method_span(src: str, sig: str) -> tuple[int, int]:
    start = src.find(sig)
    if start < 0:
        raise SystemExit(f"[step391] missing method: {sig}")
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step391] missing opening brace: {sig}")
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
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
    raise SystemExit(f"[step391] unterminated method: {sig}")


CONTENT_METHODS = r'''
    private var step391PendingContentPage: String? = null

    private fun step391StartContentImport(pageName: String) {
        step391PendingContentPage = pageName
        val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        try {
            startActivityForResult(intent, CONTENT_PICKER_REQUEST)
        } catch (t: Throwable) {
            step391PendingContentPage = null
            android.widget.Toast.makeText(this, "No file picker available", android.widget.Toast.LENGTH_SHORT).show()
        }
    }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")

    # The Step 375 page already uses the startContentImport entrypoint.
    source = source.replace("startContentImport(", "step391StartContentImport(", 1000)
    source = source.replace("private fun step391StartContentImport(pageName: String)", "private fun step391StartContentImport(pageName: String)", 1)

    if "private fun step391StartContentImport(pageName: String)" not in source:
        anchor = source.find("    companion object {")
        if anchor < 0:
            raise SystemExit("[step391] companion object anchor missing")
        source = source[:anchor] + CONTENT_METHODS + "\n" + source[anchor:]

    # Guarantee one request code declaration.
    if "private const val CONTENT_PICKER_REQUEST" not in source:
        anchor = source.find("    companion object {")
        if anchor < 0:
            raise SystemExit("[step391] companion object anchor missing for request constant")
        brace = source.find("{", anchor)
        source = source[:brace + 1] + '\n        private const val CONTENT_PICKER_REQUEST = 341' + source[brace + 1:]

    callback = "    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?)"
    start, end = method_span(source, callback)
    body = source[start:end]

    if "step391PendingContentPage" not in body:
        insert = '''        if (requestCode == CONTENT_PICKER_REQUEST && resultCode == android.app.Activity.RESULT_OK) {
            val uri = data?.data ?: return
            val pageName = step391PendingContentPage ?: return
            try {
                val temp = java.io.File.createTempFile("droid-content-", ".tmp", cacheDir)
                contentResolver.openInputStream(uri)?.use { input ->
                    java.io.FileOutputStream(temp).use { output ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val n = input.read(buffer)
                            if (n < 0) break
                            if (n > 0) output.write(buffer, 0, n)
                        }
                    }
                } ?: throw java.io.IOException("Could not open selected file")

                val kind = when (pageName) {
                    "Modpack" -> MinecraftContentManager.Kind.MODPACK
                    "Mod" -> MinecraftContentManager.Kind.MOD
                    "Shader Pack" -> MinecraftContentManager.Kind.SHADER
                    "Resource Pack" -> MinecraftContentManager.Kind.RESOURCE_PACK
                    "World" -> MinecraftContentManager.Kind.WORLD
                    else -> throw java.io.IOException("Unsupported content type: $pageName")
                }

                val installed = if (kind == MinecraftContentManager.Kind.MODPACK) {
                    if (temp.extension.equals("mrpack", true)) MinecraftModpackManager.install(this, temp)
                    else MinecraftContentManager.importArchive(this, kind, temp)
                } else {
                    MinecraftContentManager.importFile(this, kind, temp)
                }

                android.widget.Toast.makeText(this, "Installed " + installed.name, android.widget.Toast.LENGTH_LONG).show()
            } catch (t: Throwable) {
                android.widget.Toast.makeText(this, "Install failed: " + (t.message ?: "unknown error"), android.widget.Toast.LENGTH_LONG).show()
            } finally {
                step391PendingContentPage = null
            }
            return
        }
'''
        marker = "        super.onActivityResult(requestCode, resultCode, data)\n"
        if marker not in body:
            raise SystemExit("[step391] existing ActivityResult callback shape changed")
        body = body.replace(marker, marker + insert, 1)
        source = source[:start] + body + source[end:]

    # Stable marker for later audits.
    if MARKER not in source:
        callback_pos = source.find(callback)
        source = source[:callback_pos] + "    " + MARKER + "\n" + source[callback_pos:]

    # Exactly one callback is non-negotiable: cosmetic + content picker share it.
    if source.count("override fun onActivityResult(") != 1:
        raise SystemExit("[step391] ActivityResult callback count is not exactly one")
    for needle in (
        "step391StartContentImport(pageName: String)",
        "CONTENT_PICKER_REQUEST = 341",
        "requestCode == CONTENT_PICKER_REQUEST",
        'MinecraftContentManager.Kind.WORLD',
        MARKER,
    ):
        if needle not in source:
            raise SystemExit("[step391] missing content-picker contract: " + needle)

    ui.write_text(source, encoding="utf-8")
    print("[step391] final content picker merged into the single ActivityResult callback")
    print("[step391] Modpack/Mod/Shader/Resource Pack/World imports use the real Android document picker")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
