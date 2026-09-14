#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step209] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    s = s.replace('    private var serverStatusView: TextView? = null\n', '')
    start = s.find('        val serverHeader = label("Servers"')
    end = s.find('        if (saved != null) refreshServerStatus()\n', start)
    if start < 0 or end < 0:
        raise SystemExit('[step209] existing server panel not found')
    end += len('        if (saved != null) refreshServerStatus()\n')
    new_block = '''        val serverHeader = label("Servers", 17f, true)
        left.addView(serverHeader)
        left.addView(label("Saved servers · select, edit, delete, or check status", 12f, false))
        val serverList = getSavedServers()
        if (serverList.isEmpty()) {
            left.addView(label("No servers saved", 14f, true))
        } else {
            serverList.forEachIndexed { index, server ->
                val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                info.addView(label(server.first, 14f, true))
                info.addView(label(server.second.toString() + "  ·  " + getServerStatus(server.first, server.second), 12f, false))
                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
                val use = button(if (isSelectedServer(server.first, server.second)) "Selected" else "Select")
                use.setOnClickListener { selectServer(server.first, server.second); showPage("Game") }
                row.addView(use, LinearLayout.LayoutParams(dp(82), dp(42)))
                val edit = button("Edit")
                edit.setOnClickListener { showServerDialog(index) }
                row.addView(edit, LinearLayout.LayoutParams(dp(70), dp(42)))
                val del = button("Delete")
                del.setOnClickListener { deleteServer(index); showPage("Game") }
                row.addView(del, LinearLayout.LayoutParams(dp(76), dp(42)))
                val check = button("Check", true)
                check.setOnClickListener { refreshServerStatus(server.first, server.second) }
                row.addView(check, LinearLayout.LayoutParams(dp(76), dp(42)))
                left.addView(row, LinearLayout.LayoutParams(-1, dp(58)))
            }
        }
        val addServer = button("+ Add Server", true)
        addServer.setOnClickListener { showServerDialog(-1) }
        left.addView(addServer, LinearLayout.LayoutParams(-1, dp(46)))
        '''
    s = s[:start] + new_block + s[end:]
    dialog_start = s.find('    private fun showServerDialog() {')
    renderer = s.find('    private fun rendererPage() {', dialog_start)
    if dialog_start < 0 or renderer < 0:
        raise SystemExit('[step209] server dialog anchor not found')
    methods = '''    private fun showServerDialog(index: Int = -1) {
        val box = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(24), dp(8), dp(24), 0) }
        val host = android.widget.EditText(this).apply { hint = "Server address"; singleLine = true }
        val port = android.widget.EditText(this).apply { hint = "Port"; singleLine = true; inputType = android.text.InputType.TYPE_CLASS_NUMBER; setText("25565") }
        val name = android.widget.EditText(this).apply { hint = "Display name (optional)"; singleLine = true }
        val servers = getSavedServers().toMutableList()
        if (index in servers.indices) { host.setText(servers[index].first); port.setText(servers[index].second.toString()); name.setText(getServerName(index)) }
        box.addView(name, LinearLayout.LayoutParams(-1, dp(54)))
        box.addView(host, LinearLayout.LayoutParams(-1, dp(54)))
        box.addView(port, LinearLayout.LayoutParams(-1, dp(54)))
        android.app.AlertDialog.Builder(this).setTitle(if (index >= 0) "Edit Server" else "Add Server")
            .setView(box).setNegativeButton("Cancel", null)
            .setPositiveButton("Save") { _, _ ->
                val address = host.text.toString().trim()
                val serverPort = port.text.toString().trim().toIntOrNull()?.coerceIn(1, 65535) ?: 25565
                if (address.isNotBlank()) saveServerEntry(index, address, serverPort, name.text.toString().trim())
                showPage("Game")
            }.show()
    }

    private fun loadServerPrefs(): android.content.SharedPreferences = getSharedPreferences("droid_launcher", MODE_PRIVATE)

    private fun getSavedServers(): List<Pair<String, Int>> {
        val p = loadServerPrefs(); val raw = p.getString("servers", "") ?: ""
        val list = raw.split("|").filter { it.isNotBlank() }.mapNotNull {
            val x = it.split(":", limit = 2); if (x.size == 2) x[0] to (x[1].toIntOrNull() ?: return@mapNotNull null) else null
        }
        return list
    }

    private fun getServerName(index: Int): String = loadServerPrefs().getString("server_name_$index", "") ?: ""

    private fun saveServerEntry(index: Int, address: String, port: Int, name: String) {
        val p = loadServerPrefs(); val current = getSavedServers().toMutableList()
        if (index in current.indices) current[index] = address to port else current.add(address to port)
        p.edit().putString("servers", current.joinToString("|") { it.first + ":" + it.second }).apply()
        p.edit().putString("server_name_${if (index >= 0) index else current.lastIndex}", name).apply()
        selectServer(address, port)
    }

    private fun deleteServer(index: Int) {
        val current = getSavedServers().toMutableList(); if (index !in current.indices) return
        current.removeAt(index)
        loadServerPrefs().edit().putString("servers", current.joinToString("|") { it.first + ":" + it.second }).remove("server_name_$index").apply()
    }

    private fun selectServer(address: String, port: Int) {
        loadServerPrefs().edit().putString("selected_server", address + ":" + port).apply()
    }

    private fun isSelectedServer(address: String, port: Int): Boolean = loadServerPrefs().getString("selected_server", "") == address + ":" + port

    private fun getServerStatus(address: String, port: Int): String = loadServerPrefs().getString("status_$address:$port", "● Unknown") ?: "● Unknown"

    private fun refreshServerStatus(address: String, port: Int) {
        loadServerPrefs().edit().putString("status_$address:$port", "● Checking…").apply(); showPage("Game")
        Thread {
            val online = try { java.net.Socket().use { it.connect(java.net.InetSocketAddress(address, port), 1800) }; true } catch (_: Exception) { false }
            loadServerPrefs().edit().putString("status_$address:$port", if (online) "● Online" else "● Offline").apply()
            runOnUiThread { if (currentPage == "Game") showPage("Game") }
        }.start()
    }

'''
    s = s[:dialog_start] + methods + s[renderer:]
    ui.write_text(s, encoding='utf-8')
    print('[step209] multi-server list installed')
    print('[step209] selection, edit, delete, saved names and status checks installed')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
