#!/usr/bin/env python3
"""Step 223/239: expose persistent Minecraft installation state in the launcher UI."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step223] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")

    state_helper = '''    private fun minecraftInstallState(version: String): String {
        return MinecraftVersionInstallManager.state(this, version).name.replace('_', ' ')
    }

    private fun minecraftInstallProgress(version: String): String {
        return when (MinecraftVersionInstallManager.state(this, version)) {
            MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"
            MinecraftVersionInstallManager.State.DOWNLOADING -> "Downloading…"
            MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"
            MinecraftVersionInstallManager.State.NOT_INSTALLED -> "Ready to install"
        }
    }

'''
    if 'private fun minecraftInstallState(version: String)' not in s:
        anchor = '    private fun rendererPage() {'
        if anchor not in s:
            raise SystemExit('[step223] rendererPage anchor not found')
        s = s.replace(anchor, state_helper + anchor, 1)

    # Step 222 and some generated base variants can already contain this helper.
    # Add an installer only when the exact top-level function is truly absent.
    if 'private fun installMinecraftVersion(version: String)' not in s:
        install_helper = '''    private fun installMinecraftVersion(version: String) {
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
        anchor = '    private fun rendererPage() {'
        if anchor not in s:
            raise SystemExit('[step223] rendererPage anchor not found for installer helper')
        s = s.replace(anchor, install_helper + anchor, 1)

    marker = '        left.addView(label("Version  ·  $version", 13f, false))'
    replacement = marker + '\n        left.addView(label("Install  ·  ${minecraftInstallState(version)}", 12f, false))'
    if 'Install  ·  ${minecraftInstallState(version)}' not in s and marker in s:
        s = s.replace(marker, replacement, 1)

    old = '''            val choose = button(if (item == selected) "Selected" else "Select", item == selected)
            choose.setOnClickListener {
                saveMinecraftVersion(item)
                showPage("Game")
            }
            line.addView(choose, LinearLayout.LayoutParams(dp(110), dp(46)))
'''
    new = '''            val state = MinecraftVersionInstallManager.state(this, item)
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
    if old in s:
        s = s.replace(old, new, 1)

    # Fail closed if this source still contains duplicate installer declarations.
    count = s.count('    private fun installMinecraftVersion(version: String) {')
    if count != 1:
        raise SystemExit(f'[step239] installMinecraftVersion must have exactly one declaration, found {count}')

    ui.write_text(s, encoding="utf-8")
    print('[step223] persistent install state + retry UI installed')
    print('[step239] install helper ownership is now idempotent across generated launcher variants')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
