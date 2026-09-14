#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step214] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Make the server card itself open the detail page while retaining the action buttons.
    needle = '''                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val displayName = getServerName(index).trim().ifBlank { server.first }
                info.addView(label(displayName, 14f, true))'''
    replacement = '''                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                val displayName = getServerName(index).trim().ifBlank { server.first }
                info.addView(label(displayName, 14f, true))'''
    if needle not in s:
        raise SystemExit("[step214] server card info anchor not found")

    click_marker = '''                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))\n\n                val use = button(if (selected) "Selected" else "Select", selected)'''
    click_replacement = '''                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
                row.setOnClickListener { showServerDetailsPage(server.first, server.second) }

                val use = button(if (selected) "Selected" else "Select", selected)'''
    if click_marker in s:
        s = s.replace(click_marker, click_replacement, 1)

    # Prevent row click from hijacking child actions.
    for marker in [
        '                val use = button(if (selected) "Selected" else "Select", selected)',
        '                val edit = button("Edit")',
        '                val del = button("Delete")',
        '                val check = button("Check", true)'
    ]:
        if marker in s:
            s = s.replace(marker, marker + '\n                use.setOnClickListener { /* child action owns click */ }' if marker.startswith('                val use') else marker, 1)

    # Replace the accidental placeholder child listener with the actual existing listener pattern.
    s = s.replace('''                val use = button(if (selected) "Selected" else "Select", selected)
                use.setOnClickListener { /* child action owns click */ }
                use.setOnClickListener { selectServer(server.first, server.second); showPage("Game") }''', '''                val use = button(if (selected) "Selected" else "Select", selected)
                use.setOnClickListener { selectServer(server.first, server.second); showPage("Game") }''', 1)

    # Insert detail-page renderer before the main page renderer.
    anchor = '    private fun rendererPage() {'
    if 'private fun showServerDetailsPage(address: String, port: Int)' not in s:
        if anchor not in s:
            raise SystemExit("[step214] rendererPage anchor not found")
        detail = '''    private fun showServerDetailsPage(address: String, port: Int) {
        currentPage = "ServerDetails"
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(22), dp(18), dp(22), dp(18))
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val icon = TextView(this).apply {
            text = "■"
            textSize = 28f
            setTextColor(statusLabelColor(getServerStatus(address, port)))
            gravity = Gravity.CENTER
        }
        header.addView(icon, LinearLayout.LayoutParams(dp(52), dp(52)))
        val titleBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val index = getSavedServers().indexOfFirst { it.first == address && it.second == port }
        val displayName = getServerName(index).trim().ifBlank { address }
        titleBox.addView(label(displayName, 20f, true))
        titleBox.addView(label(address + ":" + port, 12f, false))
        header.addView(titleBox, LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(header, LinearLayout.LayoutParams(-1, dp(64)))

        val status = getServerStatus(address, port)
        val ping = getServerPing(address, port)
        root.addView(label(status + if (ping >= 0) "   ·   ${ping} ms" else "", 15f, true))

        val details = getServerDetails(address, port).ifBlank { "No Minecraft status data yet. Press Refresh to query the server." }
        root.addView(label(details, 13f, false))

        val infoCard = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(0x14141414)
                setStroke(dp(1), 0x33444444)
                cornerRadius = dp(10).toFloat()
            }
        }
        infoCard.addView(label("Minecraft Server", 16f, true))
        infoCard.addView(label("Address", 11f, false))
        infoCard.addView(label(address + ":" + port, 14f, true))
        if (details.contains("players")) infoCard.addView(label("Players and version are shown above from the Minecraft status response.", 11f, false))
        root.addView(infoCard, LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, dp(14), 0, dp(14)) })

        val actions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val refresh = button("↻ Refresh", true)
        refresh.setOnClickListener { refreshServerStatus(address, port); showServerDetailsPage(address, port) }
        actions.addView(refresh, LinearLayout.LayoutParams(0, dp(46), 1f))
        val select = button(if (isSelectedServer(address, port)) "Selected" else "Select")
        select.setOnClickListener { selectServer(address, port); showServerDetailsPage(address, port) }
        actions.addView(select, LinearLayout.LayoutParams(0, dp(46), 1f))
        val launch = button("▶ Join / Launch", true)
        launch.setOnClickListener { selectServer(address, port); launchExistingActivityWithServer() }
        actions.addView(launch, LinearLayout.LayoutParams(0, dp(46), 1f))
        root.addView(actions, LinearLayout.LayoutParams(-1, dp(50)))

        val back = button("← Back")
        back.setOnClickListener { showPage("Game") }
        root.addView(back, LinearLayout.LayoutParams(-1, dp(44)).apply { setMargins(0, dp(10), 0, 0) })
        setContentView(root)
    }

'''
        s = s.replace(anchor, detail + anchor, 1)

    s = s.replace('currentPage = "ServerDetails"', 'currentPage = "ServerDetails"', 1)
    ui.write_text(s, encoding="utf-8")
    print("[step214] server detail page installed")
    print("[step214] server cards open details")
    print("[step214] refresh, select and join/launch actions installed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
