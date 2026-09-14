#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step212] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Add refresh-all action near the server section without disturbing the existing layout.
    marker = '        val addServer = button("+ Add Server", true)'
    if marker in s and 'val refreshAll = button("↻ Refresh All")' not in s:
        replacement = '''        val serverActions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val refreshAll = button("↻ Refresh All")
        refreshAll.setOnClickListener { refreshAllServers() }
        serverActions.addView(refreshAll, LinearLayout.LayoutParams(0, dp(44), 1f))
        val addServer = button("+ Add Server", true)
        serverActions.addView(addServer, LinearLayout.LayoutParams(0, dp(44), 1f))
        left.addView(serverActions, LinearLayout.LayoutParams(-1, dp(46)))
        '''
        s = s.replace(marker + '\n        addServer.setOnClickListener { showServerDialog(-1) }\n        left.addView(addServer, LinearLayout.LayoutParams(-1, dp(46)))', replacement, 1)
    elif 'val refreshAll = button("↻ Refresh All")' not in s:
        raise SystemExit('[step212] Add Server marker not found')

    # Replace server row visuals with status icon + latency.
    old = '''                info.addView(label(server.second.toString() + "  ·  " + getServerStatus(server.first, server.second), 12f, false))
                val details = getServerDetails(server.first, server.second)
                if (details.isNotBlank()) info.addView(label(details, 11f, false))'''
    new = '''                val status = getServerStatus(server.first, server.second)
                val latency = getServerPing(server.first, server.second)
                info.addView(label(server.second.toString() + "  ·  " + status + if (latency >= 0) "  ·  ${latency}ms" else "", 12f, false))
                val details = getServerDetails(server.first, server.second)
                if (details.isNotBlank()) info.addView(label(details, 11f, false))'''
    if old in s:
        s = s.replace(old, new, 1)

    # Replace the status query to persist latency and use color/state text.
    old_methods = '''    private fun getServerStatus(address: String, port: Int): String = loadServerPrefs().getString("status_$address:$port", "● Unknown") ?: "● Unknown"

    private fun getServerDetails(address: String, port: Int): String = loadServerPrefs().getString("details_$address:$port", "") ?: ""

    private fun refreshServerStatus(address: String, port: Int) {'''
    new_methods = '''    private fun getServerStatus(address: String, port: Int): String = loadServerPrefs().getString("status_$address:$port", "● Unknown") ?: "● Unknown"

    private fun getServerDetails(address: String, port: Int): String = loadServerPrefs().getString("details_$address:$port", "") ?: ""

    private fun getServerPing(address: String, port: Int): Long = loadServerPrefs().getLong("ping_$address:$port", -1L)

    private fun refreshAllServers() {
        getSavedServers().forEach { refreshServerStatus(it.first, it.second) }
    }

    private fun refreshServerStatus(address: String, port: Int) {'''
    if old_methods in s:
        s = s.replace(old_methods, new_methods, 1)
    else:
        raise SystemExit('[step212] status methods anchor not found')

    old_query = '''        Thread {
            val details = queryMinecraftStatus(address, port)
            val status = if (details != null) "● Online" else "● Offline"
            loadServerPrefs().edit().putString("status_$address:$port", status).putString("details_$address:$port", details ?: "Unable to query Minecraft status").apply()
            runOnUiThread { if (currentPage == "Game") showPage("Game") }
        }.start()'''
    new_query = '''        Thread {
            val started = System.nanoTime()
            val details = queryMinecraftStatus(address, port)
            val elapsed = (System.nanoTime() - started) / 1_000_000L
            val status = if (details != null) "● Online" else "● Offline"
            loadServerPrefs().edit()
                .putString("status_$address:$port", status)
                .putLong("ping_$address:$port", if (details != null) elapsed else -1L)
                .putString("details_$address:$port", details ?: "Unable to query Minecraft status")
                .apply()
            runOnUiThread { if (currentPage == "Game") showPage("Game") }
        }.start()'''
    if old_query in s:
        s = s.replace(old_query, new_query, 1)
    else:
        raise SystemExit('[step212] query block not found')

    ui.write_text(s, encoding="utf-8")
    print("[step212] Refresh All action installed")
    print("[step212] per-server latency persistence/display installed")
    print("[step212] server state remains compatible with Minecraft status query")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
