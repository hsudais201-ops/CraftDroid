#!/usr/bin/env python3
"""Step 352: make the Microsoft-page skin/cape selectors persist real Android URIs."""
from pathlib import Path
import sys

MARKER = "// STEP352_REAL_COSMETIC_PICKER_CALLBACK"
CALLBACK = r'''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        } catch (_: Throwable) {
            // Some document providers do not support persistable permissions.
        }
        val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
        getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .edit()
            .putString(key, uri.toString())
            .apply()
        android.widget.Toast.makeText(
            this,
            if (requestCode == 3371) "Skin image selected and saved" else "Cape image selected and saved",
            android.widget.Toast.LENGTH_SHORT
        ).show()
        showMicrosoftSignInPage()
    }
    """ + MARKER + r'''"""
'''


def insert_before_class_end(source: str, block: str) -> str:
    # The generated activity is a single Kotlin class. Insert before its final
    # class brace instead of depending on a particular lifecycle method existing.
    pos = source.rfind('\n}')
    if pos < 0:
        raise SystemExit('[step352] class closing brace not found')
    return source[:pos] + '\n\n' + block + source[pos:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step352] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step352] cosmetic picker callback already installed")
        return 0

    # Older generated variants contain an onActivityResult override; newer ones
    # may not. Support both deterministically by inserting a complete override
    # immediately before the class closing brace when no existing callback exists.
    if 'override fun onActivityResult(' in s:
        anchor = "        super.onActivityResult(requestCode, resultCode, data)\n"
        if anchor not in s:
            raise SystemExit('[step352] existing onActivityResult override has unexpected shape')
        inline = CALLBACK.split('\n', 3)[3]
        # Only preserve the callback body when an override already exists.
        body = r'''        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        } catch (_: Throwable) {
            // Some document providers do not support persistable permissions.
        }
        val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
        getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .edit()
            .putString(key, uri.toString())
            .apply()
        android.widget.Toast.makeText(
            this,
            if (requestCode == 3371) "Skin image selected and saved" else "Cape image selected and saved",
            android.widget.Toast.LENGTH_SHORT
        ).show()
        showMicrosoftSignInPage()
        return
'''
        s = s.replace(anchor, anchor + body + '        ' + MARKER + '\n', 1)
    else:
        block = '''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != RESULT_OK) return
        val uri = data?.data ?: return
        try {
            contentResolver.takePersistableUriPermission(
                uri,
                android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
            )
        } catch (_: Throwable) {
            // Some document providers do not support persistable permissions.
        }
        val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
        getSharedPreferences("droid_launcher_accounts", MODE_PRIVATE)
            .edit()
            .putString(key, uri.toString())
            .apply()
        android.widget.Toast.makeText(
            this,
            if (requestCode == 3371) "Skin image selected and saved" else "Cape image selected and saved",
            android.widget.Toast.LENGTH_SHORT
        ).show()
        showMicrosoftSignInPage()
    }
    // STEP352_REAL_COSMETIC_PICKER_CALLBACK'''
        s = insert_before_class_end(s, block)

    ui.write_text(s, encoding="utf-8")
    print("[step352] real skin/cape document-picker callback installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
