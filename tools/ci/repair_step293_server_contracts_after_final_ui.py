#!/usr/bin/env python3
"""Restore the server feature contract after the Step 286 whole-UI replacement.

Also restores the authoritative modern runtime/content managers after UI generation
so the final generated source contains the complete modern feature set.
"""
from pathlib import Path
import shutil
import subprocess
import sys

MARKER = "// STEP293_SERVER_CONTRACTS"

BLOCK = r'''

// STEP293_SERVER_CONTRACTS
private fun serverPrefs(): android.content.SharedPreferences =
    getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)

private fun getSavedServers(): List<Pair<String, Int>> {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    return (0 until count).mapNotNull { i ->
        val host = prefs.getString("host_$i", "")?.trim().orEmpty()
        val port = prefs.getInt("port_$i", 25565)
        if (host.isBlank()) null else host to port.coerceIn(1, 65535)
    }
}

private fun getServerName(index: Int): String =
    serverPrefs().getString("name_$index", "")?.trim().orEmpty()

private fun getServerStatus(host: String, port: Int): String =
    serverPrefs().getString("status_${host}:$port", "Unknown") ?: "Unknown"

private fun selectServer(host: String, port: Int) {
    getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
        .putString("selected_server", "$host:$port")
        .apply()
    refreshServerStatus(host, port)
}

private fun deleteServer(index: Int) {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    if (index !in 0 until count) return
    val edit = prefs.edit()
    for (i in index until count - 1) {
        edit.putString("host_$i", prefs.getString("host_${i + 1}", "") ?: "")
            .putInt("port_$i", prefs.getInt("port_${i + 1}", 25565))
            .putString("name_$i", prefs.getString("name_${i + 1}", "") ?: "")
    }
    edit.remove("host_${count - 1}")
        .remove("port_${count - 1}")
        .remove("name_${count - 1}")
        .putInt("count", count - 1)
        .apply()
}

private fun showServerDialog(index: Int) {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    val valid = index in 0 until count
    val box = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(24), 0, dp(24), 0)
    }
    val name = android.widget.EditText(this).apply {
        hint = "Server name"
        singleLine = true
        if (valid) setText(prefs.getString("name_$index", "") ?: "")
    }
    val host = android.widget.EditText(this).apply {
        hint = "Address, e.g. play.example.com"
        singleLine = true
        if (valid) setText(prefs.getString("host_$index", "") ?: "")
    }
    val port = android.widget.EditText(this).apply {
        hint = "Port"
        singleLine = true
        inputType = android.text.InputType.TYPE_CLASS_NUMBER
        if (valid) setText(prefs.getInt("port_$index", 25565).toString()) else setText("25565")
    }
    box.addView(name, LinearLayout.LayoutParams(-1, dp(54)))
    box.addView(host, LinearLayout.LayoutParams(-1, dp(54)))
    box.addView(port, LinearLayout.LayoutParams(-1, dp(54)))
    android.app.AlertDialog.Builder(this)
        .setTitle(if (valid) "Edit Server" else "Add Server")
        .setView(box)
        .setNegativeButton("Cancel", null)
        .setPositiveButton("Save") { _, _ ->
            val cleanHost = host.text.toString().trim()
            val cleanName = name.text.toString().trim().ifBlank { cleanHost }
            val cleanPort = port.text.toString().toIntOrNull()?.coerceIn(1, 65535) ?: 25565
            if (cleanHost.isBlank()) {
                Toast.makeText(this, "Server address is required", Toast.LENGTH_LONG).show()
                return@setPositiveButton
            }
            val currentCount = prefs.getInt("count", 0).coerceIn(0, 256)
            val target = if (valid) index else currentCount
            prefs.edit()
                .putInt("count", if (valid) currentCount else currentCount + 1)
                .putString("host_$target", cleanHost)
                .putInt("port_$target", cleanPort)
                .putString("name_$target", cleanName)
                .putString("status_$cleanHost:$cleanPort", "Not checked")
                .apply()
            selectServer(cleanHost, cleanPort)
            showPage("Game")
        }.show()
}

private fun refreshServerStatus(host: String, port: Int) {
    val key = "status_$host:$port"
    serverPrefs().edit().putString(key, "Checking…").apply()
    Thread {
        val status = try {
            java.net.Socket().use { socket ->
                socket.connect(java.net.InetSocketAddress(host, port), 2500)
            }
            "Online"
        } catch (_: Throwable) {
            "Offline"
        }
        runOnUiThread {
            serverPrefs().edit().putString(key, status).apply()
            if (currentPage == "Game") showPage("Game")
        }
    }.start()
}
'''


def copy_modern_sources(root: Path) -> None:
    project = Path.cwd().resolve()
    src = project / "app/src/main/java/com/example/launcher"
    dst = root / "app/src/main/java/com/example/launcher"
    dst.mkdir(parents=True, exist_ok=True)
    names = (
        "MinecraftRuntimeProfile.kt",
        "MinecraftLatestVersionManager.kt",
        "MinecraftContentManager.kt",
        "MinecraftModpackManager.kt",
        "MinecraftLoaderProfile.kt",
        "LauncherBackgroundInstallController.kt",
        "DroidLauncherUpdateManager.kt",
    )
    missing = [name for name in names if not (src / name).is_file()]
    if missing:
        raise SystemExit(f"[step327] missing repository modern sources: {', '.join(missing)}")
    for name in names:
        shutil.copy2(src / name, dst / name)
    print(f"[step327] restored {len(names)} runtime/content/update sources into generated tree")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step293] missing UI source: {ui}")
    source = ui.read_text(encoding="utf-8")
    if MARKER not in source:
        anchor = "    private fun rendererPage() {"
        if anchor not in source:
            raise SystemExit("[step293] rendererPage anchor missing")
        source = source.replace(anchor, BLOCK + "\n" + anchor, 1)
        ui.write_text(source, encoding="utf-8")
    source = ui.read_text(encoding="utf-8")
    for needle in (
        'private fun showServerDialog(index: Int)',
        'private fun getSavedServers(): List<Pair<String, Int>>',
        'private fun getServerName(index: Int): String',
        'private fun getServerStatus(host: String, port: Int): String',
        'private fun refreshServerStatus(host: String, port: Int)',
        'private fun deleteServer(index: Int)',
        'private fun selectServer(host: String, port: Int)',
        'Thread {',
    ):
        if needle not in source:
            raise SystemExit(f"[step293] missing server contract: {needle}")
    copy_modern_sources(root)

    # Apply Step 328 only after the whole-UI replacement and manager restoration,
    # so the dynamic Mojang latest-release wiring cannot be overwritten later.
    latest_script = project_script = Path.cwd().resolve() / "tools/ci/repair_step328_latest_version_wiring.py"
    if latest_script.is_file():
        subprocess.run([sys.executable, str(latest_script), str(root)], check=True)
    else:
        raise SystemExit("[step328] latest-version wiring script missing")

    print("[step293] self-contained server Add/Edit/Delete/Select/Refresh contracts installed")
    print("[step293] server reachability checks run off the Android UI thread")
    print("[step328] latest-version wiring applied after final UI replacement")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
