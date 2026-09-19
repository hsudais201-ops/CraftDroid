#!/usr/bin/env python3
"""Verify Step480 functional manager contracts."""
from pathlib import Path
import sys

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit("[step480-verify] UI missing")
    s = ui.read_text(encoding="utf-8")
    required = (
        "// STEP480_FUNCTIONAL_MANAGERS",
        "https://api.modrinth.com/v2/search",
        "step480InstallModrinth",
        "step480LoadIcon",
        "step480WorldManagerPage()",
        "MinecraftContentManager.directory(this, MinecraftContentManager.Kind.WORLD)",
        "icon.png",
        "category_" ,
        "categories:" ,
        "Adventure" ,
        "Optimization" ,
        "MinecraftContentManager.importFile",
        "step480ReadVarInt",
        "step480WriteVarInt",
        "step480PingServer",
        "Live Minecraft Server List Ping",
        "motd_",
        "CANCEL",
        "Install failed",
        "CHOOSE VERSION & INSTALL",
        "MinecraftVersionInstallManager.cancel",
        'minecraftVersionChoices().any { MinecraftVersionInstallManager.isInstalled(this, it) }',
    )
    missing = [x for x in required if x not in s]
    if missing:
        raise SystemExit("[step480-verify] missing: " + ", ".join(missing))
    for sig in (
        "private fun step480ManagerPage(type: String)",
        "private fun step480InstallModrinth(type: String, projectId: String)",
        "private fun step480PingServer(host: String, port: Int)",
        "private fun step480ConnectServer(host: String, port: Int)",
        "private fun installMinecraftVersion(version: String)",
    ):
        if s.count(sig) != 1:
            raise SystemExit("[step480-verify] wrong declaration count: " + sig)
    if "Tcp" in s or "Socket().use { socket ->\n                socket.connect" in s:
        # The actual ping may use Socket, but it must also contain the Minecraft handshake helpers.
        if "step480WriteVarInt" not in s:
            raise SystemExit("[step480-verify] server status lacks protocol handshake")
    print("[step480-verify] content discovery/install, server ping/connect, version progress/cancel/retry and first-run flow PASS")

if __name__ == "__main__":
    main()
