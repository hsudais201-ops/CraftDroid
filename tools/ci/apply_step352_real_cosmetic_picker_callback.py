#!/usr/bin/env python3
"""Step 352: real Microsoft-page skin/cape callback plus final helper boundary repair."""
from pathlib import Path
import re
import sys

MARKER = "// STEP352_REAL_COSMETIC_PICKER_CALLBACK"


def insert_before_class_end(source: str, block: str) -> str:
    # The generated activity is a single Kotlin class. Insert before its final
    # class brace instead of depending on a particular lifecycle method existing.
    pos = source.rfind('\n}')
    if pos < 0:
        raise SystemExit('[step352] class closing brace not found')
    return source[:pos] + '\n\n' + block + source[pos:]


def repair_server_helper_boundary(source: str) -> str:
    """Repair the late-generator variant that truncates serverPrefs()."""
    patterns = (
        (
            r'(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n'
            r'\s*private fun getSavedServers\(\): List<Pair<String, Int>>\s*\{',
            '    private fun serverPrefs(): android.content.SharedPreferences =\n'
            '        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n\n'
            '    private fun getSavedServers(): List<Pair<String, Int>> {'
        ),
        (
            r'(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n'
            r'\s*private fun getSavedServers\(\)\s*\{',
            '    private fun serverPrefs(): android.content.SharedPreferences =\n'
            '        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n\n'
            '    private fun getSavedServers(): List<Pair<String, Int>> {'
        ),
    )
    for pattern, replacement in patterns:
        source = re.sub(pattern, replacement, source, count=1)
    for name in ('getSavedServers', 'getServerName', 'getServerStatus', 'selectServer', 'deleteServer', 'showServerDialog', 'refreshServerStatus'):
        source = re.sub(r'(?m)^private fun ' + re.escape(name) + r'\b', '    private fun ' + name, source)
    return source


def callback_body() -> str:
    return '''    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != android.app.Activity.RESULT_OK) return
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
        getSharedPreferences("droid_launcher_accounts", android.content.Context.MODE_PRIVATE)
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
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step352] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Always repair the server helper boundary, even when the cosmetic callback
    # marker already exists. This prevents the idempotent fast path from hiding a
    # separate generated Kotlin scope regression.
    s = repair_server_helper_boundary(s)

    if MARKER not in s:
        if 'override fun onActivityResult(' in s:
            anchor = "        super.onActivityResult(requestCode, resultCode, data)\n"
            if anchor not in s:
                raise SystemExit('[step352] existing onActivityResult override has unexpected shape')
            body = '''        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != android.app.Activity.RESULT_OK) return
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
        getSharedPreferences("droid_launcher_accounts", android.content.Context.MODE_PRIVATE)
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
            s = insert_before_class_end(s, callback_body() + '    // ' + MARKER)

    s = repair_server_helper_boundary(s)
    ui.write_text(s, encoding="utf-8")

    final = ui.read_text(encoding="utf-8")
    required = (
        "getSharedPreferences(\"droid_launcher_servers\", MODE_PRIVATE)",
        "private fun getSavedServers(): List<Pair<String, Int>> {",
        "private fun showMicrosoftSignInPage()",
        "override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?)",
        MARKER,
    )
    missing = [x for x in required if x not in final]
    if missing:
        raise SystemExit("[step352] missing final contract(s): " + ", ".join(missing))
    if 'private fun serverPrefs(): android.content.SharedPreferences =\n    private fun getSavedServers' in final:
        raise SystemExit('[step352] truncated serverPrefs declaration remains')
    print("[step352] cosmetic callback + server helper boundary repaired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
