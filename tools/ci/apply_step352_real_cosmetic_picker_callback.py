#!/usr/bin/env python3
"""Step 352/358: keep real cosmetic picker callbacks and harden generated Kotlin nullability."""
from pathlib import Path
import re
import sys

MARKER = "// STEP352_REAL_COSMETIC_PICKER_CALLBACK"


def insert_before_class_end(source: str, block: str) -> str:
    pos = source.rfind('\n}')
    if pos < 0:
        raise SystemExit('[step352] class closing brace not found')
    return source[:pos] + '\n\n' + block + source[pos:]


def repair_server_helper_boundary(source: str) -> str:
    patterns = (
        (r'(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n\s*private fun getSavedServers\(\): List<Pair<String, Int>>\s*\{',
         '    private fun serverPrefs(): android.content.SharedPreferences =\n        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n\n    private fun getSavedServers(): List<Pair<String, Int>> {'),
        (r'(?ms)^\s*private fun serverPrefs\(\): android\.content\.SharedPreferences\s*=\s*\n\s*private fun getSavedServers\(\)\s*\{',
         '    private fun serverPrefs(): android.content.SharedPreferences =\n        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n\n    private fun getSavedServers(): List<Pair<String, Int>> {'),
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
            contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION)
        } catch (_: Throwable) { }
        val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
        getSharedPreferences("droid_launcher_accounts", android.content.Context.MODE_PRIVATE)
            .edit().putString(key, uri.toString()).apply()
        android.widget.Toast.makeText(this,
            if (requestCode == 3371) "Skin image selected and saved" else "Cape image selected and saved",
            android.widget.Toast.LENGTH_SHORT).show()
        showMicrosoftSignInPage()
    }
'''


def harden_generated_nullability(root: Path) -> None:
    base = root / 'app/src/main/java/com/example'
    replacements = {
        base / 'auth/ElyByAccountProvider.kt': [
            ('json.optString("refresh_token", null)', 'json.optString("refresh_token").takeIf { it.isNotBlank() }'),
            ('skinObj.optString("url", null)', 'skinObj.optString("url").takeIf { it.isNotBlank() }'),
            ('capeObj.optString("url", null)', 'capeObj.optString("url").takeIf { it.isNotBlank() }'),
        ],
        base / 'minecraft/FabricLoaderInstaller.kt': [
            ('lib.optString("sha1", null).takeIf { !it.isNullOrBlank() }', 'lib.optString("sha1").takeIf { it.isNotBlank() }'),
            ('lib.optString("sha1", null)', 'lib.optString("sha1").takeIf { it.isNotBlank() }'),
        ],
        base / 'versions/VersionJsonParser.kt': [
            ('root.optString("assets", null)', 'root.optString("assets").takeIf { it.isNotBlank() }'),
            ('file.optString("sha1", null)', 'file.optString("sha1").takeIf { it.isNotBlank() }'),
        ],
        base / 'launcher/MinecraftLaunchCommandBuilder.kt': [
            ('System.getProperty("os.arch", "").lowercase()', '(System.getProperty("os.arch", "") ?: "").lowercase()'),
        ],
    }
    for path, pairs in replacements.items():
        if not path.is_file():
            continue
        text = path.read_text(encoding='utf-8')
        original = text
        for old, new in pairs:
            text = text.replace(old, new)
        if text != original:
            path.write_text(text, encoding='utf-8')
            print(f'[step358] hardened {path.relative_to(root)}')


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step352] missing UI source: {ui}")
    s = repair_server_helper_boundary(ui.read_text(encoding="utf-8"))
    if MARKER not in s:
        if 'override fun onActivityResult(' in s:
            anchor = "        super.onActivityResult(requestCode, resultCode, data)\n"
            if anchor not in s:
                raise SystemExit('[step352] existing onActivityResult override has unexpected shape')
            body = callback_body().replace('    override fun onActivityResult', '        override fun onActivityResult', 1).rstrip('\n')
            # Existing method: replace only its body by inserting the real persistence path.
            s = s.replace(anchor, anchor + '''        if (requestCode != 3371 && requestCode != 3372) return
        if (resultCode != android.app.Activity.RESULT_OK) return
        val uri = data?.data ?: return
        try { contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) } catch (_: Throwable) { }
        val key = if (requestCode == 3371) "microsoft_skin_uri" else "microsoft_cape_uri"
        getSharedPreferences("droid_launcher_accounts", android.content.Context.MODE_PRIVATE).edit().putString(key, uri.toString()).apply()
        showMicrosoftSignInPage()
        // STEP352_REAL_COSMETIC_PICKER_CALLBACK
''', 1)
        else:
            s = insert_before_class_end(s, callback_body() + '    // ' + MARKER)
    s = repair_server_helper_boundary(s)
    ui.write_text(s, encoding="utf-8")
    harden_generated_nullability(root)
    final = ui.read_text(encoding="utf-8")
    required = ('getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)', 'private fun getSavedServers(): List<Pair<String, Int>> {', 'private fun showMicrosoftSignInPage()', MARKER)
    missing = [x for x in required if x not in final]
    if missing:
        raise SystemExit('[step352] missing final contract(s): ' + ', '.join(missing))
    if 'private fun serverPrefs(): android.content.SharedPreferences =\n    private fun getSavedServers' in final:
        raise SystemExit('[step352] truncated serverPrefs declaration remains')
    print('[step358] cosmetic callback, server boundary, and generated nullability hardening complete')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
