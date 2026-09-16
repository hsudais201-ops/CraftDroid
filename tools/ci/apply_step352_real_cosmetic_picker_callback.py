#!/usr/bin/env python3
"""Step 352: make the Microsoft-page skin/cape selectors persist real Android URIs."""
from pathlib import Path
import sys

MARKER = "// STEP352_REAL_COSMETIC_PICKER_CALLBACK"
INSERT = r'''        if (requestCode == 3371 || requestCode == 3372) {
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
        }
'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step352] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step352] cosmetic picker callback already installed")
        return 0
    anchor = "        super.onActivityResult(requestCode, resultCode, data)\n"
    if anchor not in s:
        raise SystemExit("[step352] onActivityResult anchor missing")
    s = s.replace(anchor, anchor + INSERT + "        " + MARKER + "\n", 1)
    ui.write_text(s, encoding="utf-8")
    print("[step352] real skin/cape document-picker callback installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
