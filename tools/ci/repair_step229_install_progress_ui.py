#!/usr/bin/env python3
"""Step 229: expose live install progress plus cancel/resume controls in the launcher UI."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.exists():
        raise SystemExit(f'[step229] missing UI source: {ui}')
    s = ui.read_text(encoding='utf-8')

    old_helper = '''    private fun minecraftInstallProgress(version: String): String {
        return when (MinecraftVersionInstallManager.state(this, version)) {
            MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"
            MinecraftVersionInstallManager.State.DOWNLOADING -> "Downloading…"
            MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"
            MinecraftVersionInstallManager.State.NOT_INSTALLED -> "Ready to install"
        }
    }
'''
    new_helper = '''    private fun minecraftInstallProgress(version: String): String {
        val progress = MinecraftVersionInstallManager.savedProgress(this, version)
        val state = MinecraftVersionInstallManager.state(this, version)
        val percent = if (progress.total > 0L) ((progress.downloaded * 100L) / progress.total).coerceIn(0L, 100L) else null
        return when {
            state == MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"
            state == MinecraftVersionInstallManager.State.DOWNLOADING && percent != null -> "${percent}% · ${progress.stage}"
            state == MinecraftVersionInstallManager.State.DOWNLOADING -> progress.stage
            state == MinecraftVersionInstallManager.State.FAILED && MinecraftVersionInstallManager.lastError(this, version) == "Installation cancelled" -> "Paused · tap Resume"
            state == MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"
            else -> "Ready to install"
        }
    }
'''
    if old_helper in s:
        s = s.replace(old_helper, new_helper, 1)
    elif 'savedProgress(this, version)' not in s:
        raise SystemExit('[step229] expected install-progress helper not found')

    old_install = '''    private fun installMinecraftVersion(version: String) {
        saveMinecraftVersion(version)
        Toast.makeText(this, "Installing Minecraft $version…", Toast.LENGTH_SHORT).show()
        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {
            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                runOnUiThread { showPage("Search by ID") }
            }

            override fun onComplete(version: String) {
                runOnUiThread {
                    Toast.makeText(this@DroidLauncherUiActivity, "Minecraft $version installed", Toast.LENGTH_LONG).show()
                    showPage("Game")
                }
            }

            override fun onError(version: String, error: Throwable) {
                runOnUiThread {
                    Toast.makeText(
                        this@DroidLauncherUiActivity,
                        "Install failed: ${error.message ?: "unknown error"}",
                        Toast.LENGTH_LONG
                    ).show()
                    showPage("Search by ID")
                }
            }
        })
    }

'''
    new_install = '''    private fun installMinecraftVersion(version: String) {
        saveMinecraftVersion(version)
        Toast.makeText(this, "Installing Minecraft $version…", Toast.LENGTH_SHORT).show()
        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {
            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                runOnUiThread { showPage("Search by ID") }
            }

            override fun onComplete(version: String) {
                runOnUiThread {
                    Toast.makeText(this@DroidLauncherUiActivity, "Minecraft $version installed", Toast.LENGTH_LONG).show()
                    showPage("Game")
                }
            }

            override fun onError(version: String, error: Throwable) {
                runOnUiThread {
                    val message = if (MinecraftVersionInstallManager.lastError(this@DroidLauncherUiActivity, version) == "Installation cancelled") {
                        "Installation paused. Tap Resume to continue."
                    } else {
                        "Install failed: ${error.message ?: "unknown error"}"
                    }
                    Toast.makeText(this@DroidLauncherUiActivity, message, Toast.LENGTH_LONG).show()
                    showPage("Search by ID")
                }
            }
        })
    }

    private fun cancelMinecraftVersionInstall(version: String) {
        MinecraftVersionInstallManager.cancel(this, version)
        Toast.makeText(this, "Minecraft $version installation paused", Toast.LENGTH_SHORT).show()
        showPage("Search by ID")
    }

'''
    if old_install in s:
        s = s.replace(old_install, new_install, 1)

    old_line = '''            val state = MinecraftVersionInstallManager.state(this, item)
            val installed = MinecraftVersionInstallManager.isInstalled(this, item)
            val installButton = button(if (installed) "Installed" else "Install")
            installButton.setOnClickListener {
                if (installed) {
                    saveMinecraftVersion(item)
                    showPage("Game")
                } else {
                    installMinecraftVersion(item)
                }
            }
            line.addView(installButton, LinearLayout.LayoutParams(dp(110), dp(46)))
            info.addView(label("${state.name.replace('_', ' ')}  ·  ${minecraftInstallProgress(item)}", 11f, false))
'''
    new_line = '''            val state = MinecraftVersionInstallManager.state(this, item)
            val installed = MinecraftVersionInstallManager.isInstalled(this, item)
            val paused = state == MinecraftVersionInstallManager.State.FAILED &&
                MinecraftVersionInstallManager.lastError(this, item) == "Installation cancelled"
            val action = when {
                installed -> button("Installed", true)
                state == MinecraftVersionInstallManager.State.DOWNLOADING -> button("Cancel")
                paused -> button("Resume")
                else -> button("Install")
            }
            action.setOnClickListener {
                when {
                    installed -> { saveMinecraftVersion(item); showPage("Game") }
                    state == MinecraftVersionInstallManager.State.DOWNLOADING -> cancelMinecraftVersionInstall(item)
                    else -> installMinecraftVersion(item)
                }
            }
            line.addView(action, LinearLayout.LayoutParams(dp(110), dp(46)))
            info.addView(label("${state.name.replace('_', ' ')}  ·  ${minecraftInstallProgress(item)}", 11f, false))
'''
    if old_line in s:
        s = s.replace(old_line, new_line, 1)
    elif 'cancelMinecraftVersionInstall(item)' not in s:
        raise SystemExit('[step229] version selector install row not found')

    ui.write_text(s, encoding='utf-8')
    print('[step229] live persisted installation status exposed in version UI')
    print('[step229] Cancel/Pause and Resume controls wired')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
