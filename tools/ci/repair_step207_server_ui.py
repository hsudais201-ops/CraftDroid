#!/usr/bin/env python3
from pathlib import Path
import sys

MARKER = '        val add = button("+  Add Account")\n        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))\n'
INSERT = '''        val add = button("+  Add Account")
        left.addView(add, LinearLayout.LayoutParams(-1, dp(48)))

        val serverHeader = label("Servers", 17f, true)
        left.addView(serverHeader)
        left.addView(label("Quick server status and management", 12f, false))
        val serverRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val serverInfo = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        serverInfo.addView(label("No server added", 14f, true))
        serverInfo.addView(label("● Offline", 12f, false))
        serverRow.addView(serverInfo, LinearLayout.LayoutParams(0, -2, 1f))
        val addServer = button("+ Add Server", true)
        addServer.setOnClickListener { showServerDialog() }
        serverRow.addView(addServer, LinearLayout.LayoutParams(dp(130), dp(44)))
        left.addView(serverRow, LinearLayout.LayoutParams(-1, dp(58)))
'''

DIALOG = '''
    private fun showServerDialog() {
        val dialog = android.app.AlertDialog.Builder(this)
            .setTitle("Add Server")
            .setMessage("Server management is ready for address/port integration.\n\nStatus: Offline")
            .setPositiveButton("OK", null)
            .create()
        dialog.show()
    }
'''


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step207] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    if 'val serverHeader = label("Servers"' not in source:
        if MARKER not in source:
            raise SystemExit("[step207] expected Game page account block not found")
        source = source.replace(MARKER, INSERT, 1)
    if "private fun showServerDialog()" not in source:
        anchor = "    private fun rendererPage() {"
        if anchor not in source:
            raise SystemExit("[step207] rendererPage anchor not found")
        source = source.replace(anchor, DIALOG + "\n" + anchor, 1)
    ui.write_text(source, encoding="utf-8")
    print("[step207] home server panel installed")
    print("[step207] server status and Add Server action wired")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
