#!/usr/bin/env python3
"""Step 481: correct archive installs, real server icons and worker cleanup."""
from pathlib import Path
import sys

MARKER = "// STEP481_RUNTIME_FINISHING"

def span(src, sig):
    a = src.find(sig)
    if a < 0:
        raise SystemExit("[step481] missing " + sig)
    brace = src.find("{", a)
    if brace < 0:
        raise SystemExit("[step481] missing brace " + sig)
    depth = 0
    state = "code"
    esc = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
        if state == "line":
            if c == "\n": state = "code"
            i += 1; continue
        if state == "block":
            if c == "*" and n == "/": state = "code"; i += 2
            else: i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"': state = "code"; i += 3
            else: i += 1
            continue
        if state == "string":
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': state = "code"
            i += 1; continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = "triple"; i += 3; continue
        if c == '"': state = "string"; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return a, i + 1
        i += 1
    raise SystemExit("[step481] unterminated " + sig)

def replace(src, sig, new):
    a, b = span(src, sig)
    return src[:a] + new + src[b:]

HELPERS = r'''
    // STEP481_RUNTIME_FINISHING
    private fun step481ServerIcon(host: String, port: Int): android.widget.ImageView =
        android.widget.ImageView(this).apply {
            setImageResource(android.R.drawable.ic_menu_share)
            scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
            val raw = getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)
                .getString("favicon_" + host + ":" + port, "") ?: ""
            if (raw.startsWith("data:image/") && raw.contains(",")) {
                try {
                    val encoded = raw.substringAfter(",", "")
                    val bytes = android.util.Base64.decode(encoded, android.util.Base64.DEFAULT)
                    val options = android.graphics.BitmapFactory.Options().apply {
                        inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
                        inSampleSize = 2
                    }
                    val bmp = android.graphics.BitmapFactory.decodeByteArray(bytes, 0, bytes.size, options)
                    if (bmp != null) setImageBitmap(bmp)
                } catch (_: Throwable) {}
            }
            background = android.graphics.drawable.GradientDrawable().apply {
                cornerRadius = dp(12).toFloat()
                setColor(android.graphics.Color.argb(70, 20, 35, 48))
            }
        }

    private fun step481ReplaceContentDownloadKind(
        kind: MinecraftContentManager.Kind,
        temp: java.io.File,
        fileName: String
    ) {
        when (kind) {
            MinecraftContentManager.Kind.MODPACK,
            MinecraftContentManager.Kind.WORLD -> {
                if (fileName.lowercase().endsWith(".zip") ||
                    fileName.lowercase().endsWith(".mrpack") ||
                    fileName.lowercase().endsWith(".jar")) {
                    MinecraftContentManager.importArchive(this, kind, temp)
                } else {
                    MinecraftContentManager.importFile(this, kind, temp, fileName)
                }
            }
            else -> MinecraftContentManager.importFile(this, kind, temp, fileName)
        }
    }
'''

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step481] UI missing")
    s = ui.read_text(encoding="utf-8")

    if MARKER not in s:
        pos = s.find("    override fun onCreate(")
        if pos < 0:
            raise SystemExit("[step481] onCreate anchor missing")
        s = s[:pos] + HELPERS + "\n" + s[pos:]

    old = '                MinecraftContentManager.importFile(this, kind, tmp, fileName)'
    if old not in s:
        raise SystemExit("[step481] content install call missing")
    s = s.replace(old, '                step481ReplaceContentDownloadKind(kind, tmp, fileName)', 1)

    old = '            row.addView(step460MiniBadge("SRV"), LinearLayout.LayoutParams(dp(54), dp(54)))'
    if old not in s:
        raise SystemExit("[step481] server icon row missing")
    s = s.replace(
        old,
        '            row.addView(step481ServerIcon(host, port), LinearLayout.LayoutParams(dp(54), dp(54)))',
        1,
    )

    old = '                    val players = json.optJSONObject("players")'
    if old not in s:
        raise SystemExit("[step481] server ping players anchor missing")
    s = s.replace(
        old,
        '                    getSharedPreferences("droid_launcher_servers", MODE_PRIVATE).edit()' + "\n" +
        '                        .putString("favicon_" + host + ":" + port, json.optString("favicon", ""))' + "\n" +
        '                        .apply()' + "\n" +
        '                    val players = json.optJSONObject("players")',
        1,
    )

    # Ensure executor threads do not survive Activity destruction.
    on_destroy_sig = "    override fun onDestroy()"
    if on_destroy_sig not in s:
        raise SystemExit("[step481] onDestroy missing")
    a, b = span(s, on_destroy_sig)
    block = s[a:b]
    if "step480Executor" in s and "shutdownNow()" not in block:
        block = block.replace(
            "    override fun onDestroy() {",
            "    override fun onDestroy() {\n        try { step480Executor.shutdownNow() } catch (_: Throwable) {}",
            1,
        )
        s = s[:a] + block + s[b:]

    ui.write_text(s, encoding="utf-8")
    print("[step481] archive installs, real server favicon rendering and worker cleanup applied")

if __name__ == "__main__":
    main()
