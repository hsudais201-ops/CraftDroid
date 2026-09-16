#!/usr/bin/env python3
"""Step 342: turn the 3.jpeg Install buttons into real local-content import actions."""
from pathlib import Path
import re
import sys

MARKER = "// STEP342_CONTENT_INSTALL_PICKER"
METHODS = r'''
    private var pendingContentPage: String? = null

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != CONTENT_PICKER_REQUEST || resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        val pageName = pendingContentPage ?: return
        try {
            val temp = java.io.File.createTempFile("droid-content-", ".tmp", cacheDir)
            contentResolver.openInputStream(uri)?.use { input ->
                java.io.FileOutputStream(temp).use { output ->
                    val buffer = ByteArray(64 * 1024)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        output.write(buffer, 0, n)
                    }
                }
            } ?: throw java.io.IOException("Could not open selected file")
            val kind = when (pageName) {
                "Modpack" -> MinecraftContentManager.Kind.MODPACK
                "Mod" -> MinecraftContentManager.Kind.MOD
                "Shader Pack" -> MinecraftContentManager.Kind.SHADER
                "Resource Pack" -> MinecraftContentManager.Kind.RESOURCE_PACK
                else -> null
            }
            if (kind == null) throw java.io.IOException("Unsupported content type")
            val installed = if (kind == MinecraftContentManager.Kind.MODPACK) {
                MinecraftContentManager.importArchive(this, kind, temp)
            } else {
                MinecraftContentManager.importFile(this, kind, temp)
            }
            android.widget.Toast.makeText(this, "Installed ${installed.name}", android.widget.Toast.LENGTH_LONG).show()
        } catch (t: Throwable) {
            android.widget.Toast.makeText(this, "Install failed: ${t.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
        } finally {
            pendingContentPage = null
        }
    }

    private fun startContentImport(pageName: String) {
        pendingContentPage = pageName
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        try {
            startActivityForResult(intent, CONTENT_PICKER_REQUEST)
        } catch (t: Throwable) {
            pendingContentPage = null
            android.widget.Toast.makeText(this, "No file picker available", android.widget.Toast.LENGTH_SHORT).show()
        }
    }
'''


def inject_listener_into_action(s: str) -> str | None:
    """Attach the content picker to generated Install rows across UI variants."""
    if 'startContentImport(page)' in s:
        return s
    # Current Step 341 generated row shape.
    pattern = re.compile(
        r'(?ms)(^\s*val action = button\(if \(page == "Game"\) "↪" else "Install"\)\s*\n'
        r'\s*action\.contentDescription = if \(page == "Game"\) "Select \$name" else "Install \$name"\s*\n)'
    )
    m = pattern.search(s)
    if m:
        injected = m.group(1) + '''            action.setOnClickListener {
                if (page == "Game") {
                    selectedMinecraftVersion = name
                    android.widget.Toast.makeText(this, "Selected Minecraft $name", android.widget.Toast.LENGTH_SHORT).show()
                    libraryPage(page)
                } else {
                    startContentImport(page)
                }
            }
'''
        return s[:m.start()] + injected + s[m.end():]

    # Fallback: find any generated action variable followed by a content install label.
    generic = re.compile(r'(?ms)(^\s*val action = button\([^\n]*\)\s*\n)(\s*action\.contentDescription[^\n]*Install[^\n]*\n)')
    m = generic.search(s)
    if m:
        injected = m.group(1) + m.group(2) + '''            action.setOnClickListener {
                if (page == "Game") {
                    selectedMinecraftVersion = name
                    libraryPage(page)
                } else {
                    startContentImport(page)
                }
            }
'''
        return s[:m.start()] + injected + s[m.end():]
    return None


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    implementation_missing = (
        'private fun startContentImport(' not in s
        or 'override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?)' not in s
        or 'MinecraftContentManager.importFile' not in s
    )
    listener_missing = 'startContentImport(page)' not in s

    # Marker alone is insufficient: late UI generators can leave it while deleting
    # the implementation or the Install action. Repair the generated row first.
    repaired_listener = False
    if listener_missing:
        repaired = inject_listener_into_action(s)
        if repaired is not None:
            s = repaired
            repaired_listener = True

    if 'startContentImport(page)' not in s:
        # Older variants used a toast-only content Install branch.
        old = '''                } else {
                    android.widget.Toast.makeText(this, "Installing $name for $selectedMinecraftVersion with $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()
                }'''
        if old in s:
            s = s.replace(old, '''                } else {
                    startContentImport(page)
                }''', 1)

    if implementation_missing:
        # Remove only our known partial implementation, if any, before reinserting it.
        s = re.sub(r'(?ms)^    private var pendingContentPage: String\? = null\n.*?^    private fun startContentImport\(pageName: String\) \{.*?^    \}\n', '', s, count=1)
        companion_match = re.search(r"(?m)^[ \t]*companion object[ \t]*\{", s)
        if not companion_match:
            raise SystemExit("[step342] companion object not found")
        start, _ = companion_match.span()
        s = s[:start] + METHODS + '\n' + s[start:]

    companion_match = re.search(r"(?m)^[ \t]*companion object[ \t]*\{", s)
    if not companion_match:
        raise SystemExit("[step342] companion object not found")
    if 'CONTENT_PICKER_REQUEST' not in s:
        _, end = companion_match.span()
        s = s[:end] + '\n        private const val CONTENT_PICKER_REQUEST = 341' + s[end:]

    if MARKER not in s:
        start, _ = companion_match.span()
        s = s[:start] + '    ' + MARKER + '\n' + s[start:]

    # Fail only when all known generated shapes are genuinely absent. This keeps the
    # step strict enough to catch regressions while handling late UI rewrites.
    if 'startContentImport(page)' not in s:
        raise SystemExit("[step342] no content Install action anchor found in generated UI")

    ui.write_text(s, encoding="utf-8")
    print(f"[step342] real local import picker wired; repaired_partial={implementation_missing}; repaired_listener={repaired_listener}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
