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
            try { data?.dataString?.let { } } catch (_: Throwable) {}
        }
    }

    private fun startContentImport(pageName: String) {
        pendingContentPage = pageName
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = when (pageName) {
                "Mod" -> "*/*"
                "Modpack" -> "*/*"
                "Shader Pack" -> "*/*"
                "Resource Pack" -> "*/*"
                else -> "*/*"
            }
        }
        try {
            startActivityForResult(intent, CONTENT_PICKER_REQUEST)
        } catch (t: Throwable) {
            pendingContentPage = null
            android.widget.Toast.makeText(this, "No file picker available", android.widget.Toast.LENGTH_SHORT).show()
        }
    }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step342] content install picker already present")
        return 0
    # Replace the content-page Install branch only.
    old = '''                } else {
                    android.widget.Toast.makeText(this, "Installing $name for $selectedMinecraftVersion with $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()
                }'''
    new = '''                } else {
                    startContentImport(page)
                }'''
    if old not in s:
        raise SystemExit("[step342] Install branch not found")
    s = s.replace(old, new, 1)
    # Add request constant in companion object by inserting immediately before it.
    companion = '    companion object {\n'
    if companion not in s:
        raise SystemExit("[step342] companion object not found")
    s = s.replace(companion, '    companion object {\n        private const val CONTENT_PICKER_REQUEST = 341\n', 1)
    # Add implementation before companion object.
    s = s.replace('    companion object {\n        private const val CONTENT_PICKER_REQUEST = 341\n', METHODS + '\n    companion object {\n        private const val CONTENT_PICKER_REQUEST = 341\n', 1)
    # Marker after methods, before companion.
    s = s.replace(METHODS + '\n    companion object', '    ' + MARKER + '\n' + METHODS + '\n    companion object', 1)
    ui.write_text(s, encoding="utf-8")
    print("[step342] real local import picker wired to Modpack/Mod/Shader/Resource Pack Install buttons")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
