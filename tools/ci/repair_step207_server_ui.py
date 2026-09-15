#!/usr/bin/env python3
from pathlib import Path
import re
import sys

INSERT = '''
        val serverHeader = label("Servers", 17f, true)
        left.addView(serverHeader)
        left.addView(label("Saved server and live online/offline status", 12f, false))
        val serverRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val serverInfo = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val saved = getSavedServer()
        val serverName = label(saved?.first ?: "No server added", 14f, true)
        serverStatusView = label(
            if (saved == null) "● Offline" else saved.second.toString() + "  ·  " +
                getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("server_last_status", "● Checking…"),
            12f, false
        )
        serverInfo.addView(serverName)
        serverInfo.addView(serverStatusView)
        serverRow.addView(serverInfo, LinearLayout.LayoutParams(0, -2, 1f))
        val check = button("Check", false)
        check.setOnClickListener { refreshServerStatus() }
        serverRow.addView(check, LinearLayout.LayoutParams(dp(88), dp(44)))
        val addServer = button("+ Add Server", true)
        addServer.setOnClickListener { showServerDialog() }
        serverRow.addView(addServer, LinearLayout.LayoutParams(dp(130), dp(44)))
        left.addView(serverRow, LinearLayout.LayoutParams(-1, dp(64)))
        if (saved != null) refreshServerStatus()
'''

DIALOG = '''
    private fun showServerDialog() {
        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(8), dp(24), 0)
        }
        val host = android.widget.EditText(this).apply {
            hint = "Server address (play.example.com)"
            singleLine = true
        }
        val port = android.widget.EditText(this).apply {
            hint = "Port"
            singleLine = true
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setText("25565")
        }
        box.addView(host, LinearLayout.LayoutParams(-1, dp(54)))
        box.addView(port, LinearLayout.LayoutParams(-1, dp(54)))
        getSavedServer()?.let {
            host.setText(it.first)
            port.setText(it.second.toString())
        }
        android.app.AlertDialog.Builder(this)
            .setTitle("Add Server")
            .setView(box)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val address = host.text.toString().trim()
                val serverPort = port.text.toString().trim().toIntOrNull()?.coerceIn(1, 65535) ?: 25565
                if (address.isNotBlank()) saveServer(address, serverPort)
                showPage("Game")
            }
            .show()
    }

    private fun saveServer(address: String, port: Int) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("server_address", address)
            .putInt("server_port", port)
            .putString("server_last_status", "● Checking…")
            .apply()
        refreshServerStatus()
    }

    private fun getSavedServer(): Pair<String, Int>? {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val address = prefs.getString("server_address", null)?.trim()?.takeIf { it.isNotBlank() } ?: return null
        val port = prefs.getInt("server_port", 25565).coerceIn(1, 65535)
        return address to port
    }

    private fun refreshServerStatus() {
        val saved = getSavedServer() ?: return
        serverStatusView?.text = saved.second.toString() + "  ·  Checking…"
        Thread {
            val online = try {
                java.net.Socket().use { socket ->
                    socket.soTimeout = 1800
                    socket.connect(java.net.InetSocketAddress(saved.first, saved.second), 1800)
                }
                true
            } catch (_: Exception) {
                false
            }
            val status = if (online) "● Online" else "● Offline"
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("server_last_status", status)
                .apply()
            runOnUiThread {
                serverStatusView?.text = saved.second.toString() + "  ·  " + status
            }
        }.start()
    }
'''


def patch_manifest(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    if "android.permission.INTERNET" not in text:
        text = re.sub(r"(</manifest>)", '    <uses-permission android:name="android.permission.INTERNET" />\n\\1', text, count=1)
        manifest.write_text(text, encoding="utf-8")


def insert_server_section(source: str) -> str:
    if 'val serverHeader = label("Servers"' in source:
        return source

    # Prefer the account button added by the home/account GUI, regardless of minor
    # formatting changes made by later UI generators.
    account_patterns = [
        r'^\s*val\s+add\s*=\s*button\("\+\s*Add Account"\).*$',
        r'^\s*val\s+addAccount\s*=\s*button\("\+\s*Add Account"\).*$',
    ]
    for pattern in account_patterns:
        match = re.search(pattern, source, re.MULTILINE)
        if not match:
            continue
        line_end = source.find("\n", match.end())
        if line_end < 0:
            line_end = len(source)
        # Insert after the corresponding add-account button setup line and any
        # immediately adjacent addView line, so the server panel stays in the
        # same left-column region in all supported GUI variants.
        cursor = line_end + 1
        add_view = re.match(r'^\s*left\.addView\([^\n]+\)\s*\n', source[cursor:])
        if add_view:
            cursor += add_view.end()
        return source[:cursor] + INSERT + source[cursor:]

    # Fallback: anchor on the literal account label and its next few lines.
    label_match = re.search(r'left\.addView\([^\n]*Add Account[^\n]*\)\s*', source)
    if label_match:
        line_end = source.find("\n", label_match.end())
        if line_end < 0:
            line_end = len(source)
        return source[:line_end + 1] + INSERT + source[line_end + 1:]

    raise SystemExit("[step208] no supported Game-page Add Account anchor found")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step208] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    if "private var serverStatusView: TextView? = null" not in source:
        anchor = '    private var currentPage = "Game"\n'
        if anchor not in source:
            raise SystemExit("[step208] currentPage anchor not found")
        source = source.replace(anchor, anchor + '    private var serverStatusView: TextView? = null\n', 1)

    source = insert_server_section(source)
    start = source.find('    private fun showServerDialog() {')
    if start >= 0:
        end = source.find('    private fun rendererPage() {', start)
        if end < 0:
            raise SystemExit("[step208] rendererPage anchor not found")
        source = source[:start] + DIALOG + '\n' + source[end:]
    else:
        anchor = '    private fun rendererPage() {'
        if anchor not in source:
            raise SystemExit("[step208] rendererPage anchor not found")
        source = source.replace(anchor, DIALOG + '\n' + anchor, 1)
    ui.write_text(source, encoding="utf-8")

    manifests = list(root.glob("**/src/main/AndroidManifest.xml"))
    if manifests:
        patch_manifest(manifests[0])
    print("[step208] server name/address/port persistence installed")
    print("[step208] asynchronous TCP reachability status installed")
    print("[step208] repair now accepts final Home/Account GUI variants")
    print("[step208] INTERNET permission ensured")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
