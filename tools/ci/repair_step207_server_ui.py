#!/usr/bin/env python3
from pathlib import Path
import re
import sys

MARKER = '        val add = button("+  Add Account")\n        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))\n'
INSERT = '''        val add = button("+  Add Account")
        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))

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
        val address = prefs.getString("server_address", null) ?: return null
        return address to prefs.getInt("server_port", 25565)
    }

    private fun refreshServerStatus() {
        val saved = getSavedServer() ?: return
        serverStatusView?.text = saved.second.toString() + "  ·  Checking…"
        Thread {
            val online = try {
                java.net.Socket().use { socket ->
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
        text = re.sub(r'(</manifest>)', '    <uses-permission android:name="android.permission.INTERNET" />\n\\1', text, count=1)
        manifest.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step208] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    # Generated UI gets a field so the async reachability check can update only the status label.
    if "private var serverStatusView: TextView? = null" not in source:
        anchor = '    private var currentPage = "Game"\n'
        if anchor not in source:
            raise SystemExit("[step208] currentPage anchor not found")
        source = source.replace(anchor, anchor + '    private var serverStatusView: TextView? = null\n', 1)
    if 'val serverHeader = label("Servers"' not in source:
        if MARKER not in source:
            raise SystemExit("[step208] expected Game page account block not found")
        source = source.replace(MARKER, INSERT, 1)
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
    print("[step208] status updates no longer recurse through page rendering")
    print("[step208] INTERNET permission ensured")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
