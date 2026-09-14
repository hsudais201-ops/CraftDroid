#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step214] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    # Make each server card open a dedicated detail view. Android child buttons
    # naturally consume their own clicks, so Select/Edit/Delete/Check remain intact.
    marker = '''                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))

                val use = button(if (selected) "Selected" else "Select", selected)'''
    replacement = '''                row.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
                row.setOnClickListener { showServerDetailsPage(server.first, server.second) }

                val use = button(if (selected) "Selected" else "Select", selected)'''
    if marker in s and 'row.setOnClickListener { showServerDetailsPage(server.first, server.second) }' not in s:
        s = s.replace(marker, replacement, 1)
    elif 'row.setOnClickListener { showServerDetailsPage(server.first, server.second) }' not in s:
        raise SystemExit("[step214] server card click anchor not found")

    # Detail page: status, measured ping, MOTD/version/player summary, and actions.
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
        val status = getServerStatus(address, port)
        val icon = TextView(this).apply {
            text = "■"
            textSize = 28f
            setTextColor(statusLabelColor(status))
            gravity = Gravity.CENTER
        }
        header.addView(icon, LinearLayout.LayoutParams(dp(54), dp(54)))

        val titleBox = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val index = getSavedServers().indexOfFirst { it.first == address && it.second == port }
        val displayName = getServerName(index).trim().ifBlank { address }
        titleBox.addView(label(displayName, 20f, true))
        titleBox.addView(label(address + ":" + port, 12f, false))
        header.addView(titleBox, LinearLayout.LayoutParams(0, -2, 1f))
        root.addView(header, LinearLayout.LayoutParams(-1, dp(64)))

        val ping = getServerPing(address, port)
        root.addView(label(status + if (ping >= 0) "   ·   ${ping} ms" else "", 15f, true))

        val details = getServerDetails(address, port)
        val summary = details.ifBlank { "No Minecraft status data yet. Press Refresh to query this server." }
        root.addView(label(summary, 13f, false))

        val card = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(0x14141414)
                setStroke(dp(1), 0x33444444)
                cornerRadius = dp(10).toFloat()
            }
        }
        card.addView(label("Server information", 16f, true))
        card.addView(label("Address", 11f, false))
        card.addView(label(address + ":" + port, 14f, true))
        if (details.contains("·")) {
            card.addView(label("MOTD · Version · Players", 11f, false))
            card.addView(label(details, 13f, false))
        }
        root.addView(card, LinearLayout.LayoutParams(-1, -2).apply { setMargins(0, dp(14), 0, dp(14)) })

        val actions = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val refresh = button("↻ Refresh", true)
        refresh.setOnClickListener { refreshServerStatus(address, port) }
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

    # While a detail page is open, an async server query must repaint the detail
    # view with the fresh result rather than silently updating only preferences.
    old_async = '''            runOnUiThread { if (currentPage == "Game") showPage("Game") }
        }.start()'''
    new_async = '''            runOnUiThread {
                when (currentPage) {
                    "Game" -> showPage("Game")
                    "ServerDetails" -> showServerDetailsPage(address, port)
                }
            }
        }.start()'''
    if old_async in s and new_async not in s:
        s = s.replace(old_async, new_async, 1)

    ui.write_text(s, encoding="utf-8")
    print("[step214] server detail page installed")
    print("[step214] server cards open details while child actions remain usable")
    print("[step214] refresh, select, and join/launch actions installed")
    print("[step214] async detail refresh rendering installed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
