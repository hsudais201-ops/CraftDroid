#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step215] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    old = '''    private fun launchExistingActivityWithServer() {
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
    new = '''    private fun launchExistingActivityWithServer() {
        val saved = getSavedServer()
        val component = EXISTING_LAUNCHER_COMPONENT
        if (component.isBlank()) {
            android.widget.Toast.makeText(this, "Minecraft launch target is not configured", android.widget.Toast.LENGTH_LONG).show()
            return
        }
        if (saved == null) {
            android.widget.Toast.makeText(this, "Select or add a Minecraft server first", android.widget.Toast.LENGTH_LONG).show()
            if (currentPage != "Game") showPage("Game")
            return
        }
        val endpoint = "${saved.first}:${saved.second}"
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("last_launch_server", endpoint)
            .putLong("last_launch_started", System.currentTimeMillis())
            .putString("last_launch_state", "PREPARING")
            .apply()
        android.widget.Toast.makeText(this, "Launching Droid Launcher for $endpoint…", android.widget.Toast.LENGTH_SHORT).show()
        try {
            val parts = component.split('/', limit = 2)
            if (parts.size != 2) throw IllegalArgumentException("Invalid launch component")
            val className = parts[1].removePrefix(".")
            val intent = Intent().setClassName(packageName, className)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            intent.putExtra("server_address", saved.first)
            intent.putExtra("server_port", saved.second)
            intent.putExtra("minecraft_server", endpoint)
            intent.putExtra("launch_source", "Droid Launcher")
            intent.putExtra("launch_started_at", System.currentTimeMillis())
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("last_launch_state", "STARTING")
                .apply()
            startActivity(intent)
        } catch (e: android.content.ActivityNotFoundException) {
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit().putString("last_launch_state", "ERROR").apply()
            android.widget.Toast.makeText(this, "Launch activity not found: ${e.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit().putString("last_launch_state", "ERROR").apply()
            android.widget.Toast.makeText(this, "Minecraft launch failed: ${e.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
            try { launchExistingActivity() } catch (_: Exception) { }
        }
    }
'''
    if old not in s:
        raise SystemExit("[step215] selected-server launch method not found")
    s = s.replace(old, new, 1)

    # Add a reusable launch-state accessor for the UI and future diagnostics.
    anchor = '    private fun rendererPage() {'
    helper = '''    private fun getLastLaunchState(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("last_launch_state", "IDLE") ?: "IDLE"

    private fun getLastLaunchServer(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("last_launch_server", "") ?: ""

'''
    if 'private fun getLastLaunchState(): String' not in s and anchor in s:
        s = s.replace(anchor, helper + anchor, 1)

    ui.write_text(s, encoding="utf-8")
    print("[step215] selected-server launch validation installed")
    print("[step215] launch extras and source metadata preserved")
    print("[step215] launch progress/error feedback installed")
    print("[step215] last-launch diagnostics persisted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
