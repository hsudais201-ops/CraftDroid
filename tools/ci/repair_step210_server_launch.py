#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step210] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")

    old = 'launch.setOnClickListener { launchExistingActivity() }'
    new = 'launch.setOnClickListener { launchExistingActivityWithServer() }'
    source = source.replace(old, new, 1)

    anchor = '    private fun launchExistingActivity() {'
    if 'private fun launchExistingActivityWithServer()' not in source:
        if anchor not in source:
            raise SystemExit("[step210] launchExistingActivity anchor not found")
        method = '''    private fun launchExistingActivityWithServer() {
        val saved = getSavedServer()
        val component = EXISTING_LAUNCHER_COMPONENT
        if (component.isBlank()) return
        try {
            val parts = component.split('/', limit = 2)
            if (parts.size != 2) return
            val intent = Intent().setClassName(packageName, parts[1].removePrefix("."))
            if (saved != null) {
                intent.putExtra("server_address", saved.first)
                intent.putExtra("server_port", saved.second)
                intent.putExtra("minecraft_server", "${saved.first}:${saved.second}")
            }
            startActivity(intent)
        } catch (_: Exception) {
            launchExistingActivity()
        }
    }

'''
        source = source.replace(anchor, method + anchor, 1)

    ui.write_text(source, encoding="utf-8")
    print("[step210] selected server launch extras wired")
    print("[step210] launch safely falls back to legacy activity")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
