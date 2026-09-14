#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step213] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Step 211/212 added an automatic refresh inside page rendering. Remove it so
    # opening/rebuilding the Game page does not recursively spawn more refreshes.
    s = s.replace('        serverList.forEach { refreshServerStatus(it.first, it.second) }\n\n', '', 1)

    start = s.find('            serverList.forEachIndexed { index, server ->')
    end = s.find('        val serverActions = LinearLayout(this).apply', start)
    if start < 0 or end < 0:
        raise SystemExit('[step213] server card block not found')

    new_cards = '''            serverList.forEachIndexed { index, server ->
                val selected = isSelectedServer(server.first, server.second)
                val status = getServerStatus(server.first, server.second)
                val latency = getServerPing(server.first, server.second)
                val row = LinearLayout(this).apply {
                    orientation = LinearLayout.HORIZONTAL
                    gravity = Gravity.CENTER_VERTICAL
                    setPadding(dp(12), dp(8), dp(8), dp(8))
                    background = android.graphics.drawable.GradientDrawable().apply {
                        setColor(if (selected) 0x2233AAFF else 0x14141414)
                        setStroke(dp(1), if (selected) 0xFF33AAFF.toInt() else 0x33444444)
                        cornerRadius = dp(8).toFloat()
                    }
                }

                val dot = label(if (status.contains("Online")) "●" else if (status.contains("Checking")) "◌" else "●", 18f, false)
                dot.setTextColor(
                    when {
                        status.contains("Online") -> 0xFF55DD88.toInt()
                        status.contains("Checking") -> 0xFFFFC857.toInt()
                        else -> 0xFFE05B5B.toInt()
                    }
                )
                row.addView(dot, LinearLayout.LayoutParams(dp(28), -1))

                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val displayName = getServerName(index).trim().ifBlank { server.first }
                info.addView(label(displayName, 14f, true))
                val endpoint = server.first + ":" + server.second
                val statusLine = buildString {
                    append(endpoint)
                    append("  ·  ")
                    append(status)
                    if (latency >= 0) append("  ·  ").append(latency).append(" ms")
                }
                info.addView(label(statusLine, 12f, false))
                val details = getServerDetails(server.first, server.second)
                if (details.isNotBlank()) info.addView(label(details, 11f, false))
                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))

                val use = button(if (selected) "Selected" else "Select", selected)
                use.setOnClickListener { selectServer(server.first, server.second); showPage("Game") }
                row.addView(use, LinearLayout.LayoutParams(dp(86), dp(42)))

                val edit = button("Edit")
                edit.setOnClickListener { showServerDialog(index) }
                row.addView(edit, LinearLayout.LayoutParams(dp(68), dp(42)))

                val del = button("Delete")
                del.setOnClickListener { deleteServer(index); showPage("Game") }
                row.addView(del, LinearLayout.LayoutParams(dp(76), dp(42)))

                val check = button("Check", true)
                check.setOnClickListener { refreshServerStatus(server.first, server.second) }
                row.addView(check, LinearLayout.LayoutParams(dp(76), dp(42)))

                left.addView(row, LinearLayout.LayoutParams(-1, dp(70)).apply {
                    setMargins(0, dp(4), 0, dp(4))
                })
            }
        }
'''
    s = s[:start] + new_cards + s[end:]

    # Keep display-name persistence stable after delete operations by shifting
    # later names down and clearing the removed tail entry.
    old_delete = '''    private fun deleteServer(index: Int) {
        val current = getSavedServers().toMutableList(); if (index !in current.indices) return
        current.removeAt(index)
        loadServerPrefs().edit().putString("servers", current.joinToString("|") { it.first + ":" + it.second }).remove("server_name_$index").apply()
    }
'''
    new_delete = '''    private fun deleteServer(index: Int) {
        val current = getSavedServers().toMutableList(); if (index !in current.indices) return
        current.removeAt(index)
        val editor = loadServerPrefs().edit().putString("servers", current.joinToString("|") { it.first + ":" + it.second })
        for (i in index until current.size) editor.putString("server_name_$i", loadServerPrefs().getString("server_name_${i + 1}", "") ?: "")
        editor.remove("server_name_${current.size}")
        val selected = loadServerPrefs().getString("selected_server", "") ?: ""
        if (selected !in current.map { it.first + ":" + it.second }) editor.remove("selected_server")
        editor.apply()
    }
'''
    if old_delete in s:
        s = s.replace(old_delete, new_delete, 1)

    # Add a small style helper for future UI patches while keeping this step self-contained.
    anchor = '    private fun rendererPage() {'
    helper = '''    private fun statusLabelColor(status: String): Int = when {
        status.contains("Online") -> 0xFF55DD88.toInt()
        status.contains("Checking") -> 0xFFFFC857.toInt()
        status.contains("Offline") -> 0xFFE05B5B.toInt()
        else -> 0xFFB8B8B8.toInt()
    }

'''
    if 'private fun statusLabelColor(status: String): Int' not in s and anchor in s:
        s = s.replace(anchor, helper + anchor, 1)

    ui.write_text(s, encoding="utf-8")
    print("[step213] styled server cards with selected state")
    print("[step213] added status indicator and compact display names")
    print("[step213] removed recursive automatic refresh from page rendering")
    print("[step213] kept per-server Check and Refresh All actions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
