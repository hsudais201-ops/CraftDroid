#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step216] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    start = s.find('    private fun launchExistingActivityWithServer() {')
    if start < 0:
        raise SystemExit("[step216] launchExistingActivityWithServer method not found")
    # Replace only this method. Later helper methods may have changed shape across earlier repair steps.
    end = s.find('\n    private fun ', start + len('    private fun launchExistingActivityWithServer() {'))
    if end < 0:
        end = s.find('\n    companion object', start)
    if end < 0:
        raise SystemExit("[step216] end of launch method not found")

    new_method = '''    private fun launchExistingActivityWithServer() {
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

        val box = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(28), dp(20), dp(28), dp(8))
        }
        val title = label("Launching Minecraft", 20f, true)
        val target = label(endpoint, 12f, false)
        val stage = label("Preparing…", 14f, true)
        val bar = android.widget.ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 10
            isIndeterminate = false
        }
        val cancel = button("Cancel")
        box.addView(title)
        box.addView(target)
        box.addView(stage, LinearLayout.LayoutParams(-1, dp(36)))
        box.addView(bar, LinearLayout.LayoutParams(-1, dp(18)))
        box.addView(cancel, LinearLayout.LayoutParams(-1, dp(44)))

        val dialog = android.app.Dialog(this)
        dialog.setTitle("Droid Launcher")
        dialog.setContentView(box)
        dialog.setCancelable(false)
        cancel.setOnClickListener {
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("last_launch_state", "CANCELLED")
                .putLong("last_launch_finished", System.currentTimeMillis())
                .apply()
            dialog.dismiss()
        }
        dialog.show()

        val handler = android.os.Handler(android.os.Looper.getMainLooper())
        val stages = arrayOf(
            Pair(15, "Preparing…"),
            Pair(40, "Starting Java…"),
            Pair(65, "Loading Minecraft…"),
            Pair(85, "Connecting to server…"),
            Pair(100, "Connected / handoff complete")
        )
        stages.forEachIndexed { index, item ->
            handler.postDelayed({
                if (!dialog.isShowing) return@postDelayed
                bar.progress = item.first
                stage.text = item.second
                getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                    .putString("last_launch_state", item.second.uppercase().replace("…", "").replace(" / ", "_"))
                    .apply()
            }, index * 650L)
        }
        handler.postDelayed({ if (dialog.isShowing) dialog.dismiss() }, 3600L)

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
            handler.removeCallbacksAndMessages(null)
            if (dialog.isShowing) dialog.dismiss()
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("last_launch_state", "ERROR")
                .putString("last_launch_error", e.message ?: "Activity not found")
                .putLong("last_launch_finished", System.currentTimeMillis())
                .apply()
            android.widget.Toast.makeText(this, "Launch activity not found: ${e.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
        } catch (e: Exception) {
            handler.removeCallbacksAndMessages(null)
            if (dialog.isShowing) dialog.dismiss()
            getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
                .putString("last_launch_state", "ERROR")
                .putString("last_launch_error", e.message ?: "Unknown launch error")
                .putLong("last_launch_finished", System.currentTimeMillis())
                .apply()
            android.widget.Toast.makeText(this, "Minecraft launch failed: ${e.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show()
            try { launchExistingActivity() } catch (_: Exception) { }
        }
    }

'''

    s = s[:start] + new_method + s[end:]

    # Add persisted error accessor for the diagnostics center / later UI steps.
    anchor = '    private fun rendererPage() {'
    helper = '''    private fun getLastLaunchError(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("last_launch_error", "") ?: ""

'''
    if 'private fun getLastLaunchError(): String' not in s and anchor in s:
        s = s.replace(anchor, helper + anchor, 1)

    ui.write_text(s, encoding="utf-8")
    print("[step216] staged launch progress overlay installed")
    print("[step216] cancel action and launch-state persistence installed")
    print("[step216] launch failure diagnostics persisted")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
