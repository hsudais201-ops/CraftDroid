#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = '        val add = button("+  Add Account")\n        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))\n'
INSERT = '''        val add = button("+  Add Account")
        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))

        val serverHeader = label("Servers", 17f, true)
        left.addView(serverHeader)
        left.addView(label("Saved server and live online/offline status", 12f, false))
        val serverRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val serverInfo = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        serverInfo.addView(label("No server added", 14f, true))
        serverInfo.addView(label("● Offline", 12f, false))
        serverRow.addView(serverInfo, LinearLayout.LayoutParams(0, -2, 1f))
        val check = button("Check", false)
        check.setOnClickListener { refreshServerStatus() }
        serverRow.addView(check, LinearLayout.LayoutParams(dp(88), dp(44)))
        val addServer = button("+ Add Server", true)
        addServer.setOnClickListener { showServerDialog() }
        serverRow.addView(addServer, LinearLayout.LayoutParams(dp(130), dp(44)))
        left.addView(serverRow, LinearLayout.LayoutParams(-1, dp(64)))
        val saved = getSavedServer()
        if (saved != null) {
            serverInfo.removeAllViews()
            serverInfo.addView(label(saved.first, 14f, true))
            serverInfo.addView(label(saved.second.toString() + "  ·  checking…", 12f, false))
            refreshServerStatus()
        }
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
        val saved = getSavedServer()
        if (saved != null) {
            host.setText(saved.first)
            port.setText(saved.second.toString())
        }
        android.app.AlertDialog.Builder(this)
            .setTitle("Add Server")
            .setView(box)
            .setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val address = host.text.toString().trim()
                val serverPort = port.text.toString().trim().toIntOrNull() ?: 25565
                if (address.isNotBlank()) saveServer(address, serverPort)
                showPage("Game")
            }
            .show()
    }

    private fun saveServer(address: String, port: Int) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("server_address", address)
            .putInt("server_port", port)
            .apply()
    }

    private fun getSavedServer(): Pair<String, Int>? {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val address = prefs.getString("server_address", null) ?: return null
        return address to prefs.getInt("server_port", 25565)
    }

    private fun refreshServerStatus() {
        val saved = getSavedServer() ?: return
        val target = saved
        Thread {
            val online = try {
                val socket = java.net.Socket()
                socket.connect(java.net.InetSocketAddress(target.first, target.second), 1800)
                socket.close()
                true
            } catch (_: Exception) {
                false
            }
            runOnUiThread {
                if (currentPage == "Game") showPage("Game")
            }
        }.start()
    }
'''


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step208] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    source = source.replace(MARKER, INSERT, 1) if 'val serverHeader = label("Servers"' not in source else source
    # Replace the placeholder dialog/refresh block with the functional implementation.
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
    # The status thread must publish its result; use a tiny stable tag-based label update by rebuilding the page.
    source = source.replace('        Thread {\n            val online = try {', '        Thread {\n            val online = try {')
    source = source.replace('            runOnUiThread {\n                if (currentPage == "Game") showPage("Game")\n            }', '            runOnUiThread {\n                val status = if (online) "● Online" else "● Offline"\n                if (currentPage == "Game") {\n                    val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)\n                    prefs.edit().putString("server_last_status", status).apply()\n                    showPage("Game")\n                }\n            }')
    source = source.replace('serverInfo.addView(label(saved.second.toString() + "  ·  checking…", 12f, false))', 'serverInfo.addView(label(saved.second.toString() + "  ·  " + getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("server_last_status", "● Checking…"), 12f, false))')
    ui.write_text(source, encoding="utf-8")
    print("[step208] saved server address/port fields installed")
    print("[step208] server persistence and TCP reachability status installed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
