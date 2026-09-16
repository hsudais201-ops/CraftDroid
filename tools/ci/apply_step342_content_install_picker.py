#!/usr/bin/env python3
"""Step 342: wire Download/Install content actions to a real Android file picker."""
from pathlib import Path
import re, sys

MARKER = "// STEP342_CONTENT_INSTALL_PICKER"
METHODS = r'''
    private var pendingContentPage: String? = null

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
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
            val installed = if (kind == MinecraftContentManager.Kind.MODPACK) MinecraftContentManager.importArchive(this, kind, temp)
            else MinecraftContentManager.importFile(this, kind, temp)
            android.widget.Toast.makeText(this, "Installed ${installed.name}", android.widget.Toast.LENGTH_LONG).show()
        } catch (t: Throwable) {
            android.widget.Toast.makeText(this, "Install failed: ${t.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
        } finally { pendingContentPage = null }
    }

    private fun startContentImport(pageName: String) {
        pendingContentPage = pageName
        val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(android.content.Intent.CATEGORY_OPENABLE)
            type = "*/*"
        }
        try { startActivityForResult(intent, CONTENT_PICKER_REQUEST) }
        catch (t: Throwable) {
            pendingContentPage = null
            android.widget.Toast.makeText(this, "No file picker available", android.widget.Toast.LENGTH_SHORT).show()
        }
    }
'''

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    # Repair any generated Install action before installing the callback implementation.
    if 'startContentImport(page)' not in s:
        if 'val action = button(if (page == "Game") "↪" else "Install")' in s:
            s = s.replace('            action.contentDescription = if (page == "Game") "Select $name" else "Install $name"\n', '            action.contentDescription = if (page == "Game") "Select $name" else "Install $name"\n            action.setOnClickListener { if (page == "Game") { selectedMinecraftVersion = name } else { startContentImport(page) } }\n', 1)
        else:
            old = '                } else {\n                    android.widget.Toast.makeText(this, "Installing $name for $selectedMinecraftVersion with $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()\n                }'
            if old in s: s = s.replace(old, '                } else {\n                    startContentImport(page)\n                }', 1)
    # Replace only our known prior implementation to keep this step idempotent.
    if 'private fun startContentImport(' not in s:
        companion = re.search(r'(?m)^\s*companion object\s*\{', s)
        if not companion: raise SystemExit('[step342] companion object not found')
        s = s[:companion.start()] + METHODS + '\n' + s[companion.start():]
    # The previous check accidentally looked for a use-site reference. Require the declaration.
    companion = re.search(r'(?m)^\s*companion object\s*\{', s)
    if not companion: raise SystemExit('[step342] companion object not found')
    if 'private const val CONTENT_PICKER_REQUEST' not in s:
        s = s[:companion.end()] + '\n        private const val CONTENT_PICKER_REQUEST = 341' + s[companion.end():]
    if MARKER not in s:
        s = s[:companion.start()] + '    ' + MARKER + '\n' + s[companion.start():]
    if 'startContentImport(page)' not in s:
        raise SystemExit('[step342] no content Install action anchor found in generated UI')
    ui.write_text(s, encoding='utf-8')
    print('[step342] real local import picker wired; request-code declaration guaranteed')
    return 0

if __name__ == '__main__': raise SystemExit(main())
