#!/usr/bin/env python3
"""Step 342: turn the 3.jpeg Install buttons into real local-content import actions."""
from pathlib import Path
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step342] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step342] content install picker already present")
        return 0

    # Step341 may already have converted Install to startContentImport(page). In that
    # case only the implementation and marker remain to be installed. Older generated
    # variants used a Toast-only else branch, which is normalized here too.
    old = '''                } else {
                    android.widget.Toast.makeText(this, "Installing $name for $selectedMinecraftVersion with $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()
                }'''
    if old in s:
        s = s.replace(old, '''                } else {
                    startContentImport(page)
                }''', 1)
    elif 'startContentImport(page)' not in s:
        raise SystemExit("[step342] no content Install action anchor found")

    companion = '    companion object {\n'
    if companion not in s:
        raise SystemExit("[step342] companion object not found")
    if 'CONTENT_PICKER_REQUEST' not in s:
        s = s.replace(companion, '    companion object {\n        private const val CONTENT_PICKER_REQUEST = 341\n', 1)

    # Avoid duplicate declarations on partially patched generated sources.
    if 'private fun startContentImport(' not in s:
        s = s.replace(companion if '    companion object {\n' in s else '    companion object {', METHODS + '\n    companion object {', 1)
    if MARKER not in s:
        anchor = '    companion object {\n'
        if anchor in s:
            s = s.replace(anchor, '    ' + MARKER + '\n' + anchor, 1)
        else:
            raise SystemExit("[step342] companion insertion anchor not found")

    ui.write_text(s, encoding="utf-8")
    print("[step342] real local import picker wired to Modpack/Mod/Shader/Resource Pack Install buttons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
