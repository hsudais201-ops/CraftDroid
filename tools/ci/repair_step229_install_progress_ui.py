#!/usr/bin/env python3
"""Step 229: expose live install progress plus cancel/resume controls in the launcher UI."""
from pathlib import Path
import re
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.exists():
        raise SystemExit(f'[step229] missing UI source: {ui}')
    s = ui.read_text(encoding='utf-8')

    # Prefer the Step 223 install helper and upgrade it in-place.
    helper_start = s.find('    private fun minecraftInstallProgress(version: String): String {')
    if helper_start >= 0:
        helper_end = s.find('\n    }\n', helper_start)
        # Find the matching helper end conservatively by the next known function.
        next_fun = s.find('\n    private fun installMinecraftVersion', helper_start)
        if next_fun < 0:
            next_fun = s.find('\n    private fun rendererPage', helper_start)
        if next_fun < 0:
            raise SystemExit('[step229] could not locate install helper boundary')
        old_block = s[helper_start:next_fun]
        new_block = '''    private fun minecraftInstallProgress(version: String): String {\n        val progress = MinecraftVersionInstallManager.savedProgress(this, version)\n        val state = MinecraftVersionInstallManager.state(this, version)\n        val percent = if (progress.total > 0L) ((progress.downloaded * 100L) / progress.total).coerceIn(0L, 100L) else null\n        return when {\n            state == MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"\n            state == MinecraftVersionInstallManager.State.DOWNLOADING && percent != null -> "${percent}% · ${progress.stage}"\n            state == MinecraftVersionInstallManager.State.DOWNLOADING -> progress.stage\n            state == MinecraftVersionInstallManager.State.FAILED && MinecraftVersionInstallManager.lastError(this, version) == "Installation cancelled" -> "Paused · tap Resume"\n            state == MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"\n            else -> "Ready to install"\n        }\n    }\n\n'''
        s = s[:helper_start] + new_block + s[next_fun:]
    elif 'savedProgress(this, version)' not in s:
        raise SystemExit('[step229] install-progress helper not found')

    # Upgrade the install function by replacing the complete function body up to the next private function.
    install_start = s.find('    private fun installMinecraftVersion(version: String) {')
    if install_start < 0:
        raise SystemExit('[step229] installMinecraftVersion anchor not found')
    next_fun = s.find('\n    private fun ', install_start + 1)
    if next_fun < 0:
        raise SystemExit('[step229] install function boundary not found')
    install_block = '''    private fun installMinecraftVersion(version: String) {\n        saveMinecraftVersion(version)\n        Toast.makeText(this, "Installing Minecraft $version…", Toast.LENGTH_SHORT).show()\n        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {\n            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {\n                runOnUiThread { showPage("Search by ID") }\n            }\n\n            override fun onComplete(version: String) {\n                runOnUiThread {\n                    Toast.makeText(this@DroidLauncherUiActivity, "Minecraft $version installed", Toast.LENGTH_LONG).show()\n                    showPage("Game")\n                }\n            }\n\n            override fun onError(version: String, error: Throwable) {\n                runOnUiThread {\n                    val paused = MinecraftVersionInstallManager.lastError(this@DroidLauncherUiActivity, version) == "Installation cancelled"\n                    val message = if (paused) "Installation paused. Tap Resume to continue." else "Install failed: ${error.message ?: "unknown error"}"\n                    Toast.makeText(this@DroidLauncherUiActivity, message, Toast.LENGTH_LONG).show()\n                    showPage("Search by ID")\n                }\n            }\n        })\n    }\n\n    private fun cancelMinecraftVersionInstall(version: String) {\n        MinecraftVersionInstallManager.cancel(this, version)\n        Toast.makeText(this, "Minecraft $version installation paused", Toast.LENGTH_SHORT).show()\n        showPage("Search by ID")\n    }\n\n'''
    s = s[:install_start] + install_block + s[next_fun:]

    # Locate the actual version-card action row by identifying a row that contains version state/install UI.
    if 'cancelMinecraftVersionInstall(item)' not in s:
        pattern = re.compile(
            r'(?P<indent>\s*)val state = MinecraftVersionInstallManager\.state\(this, item\).*?\n(?P<tail>\s*info\.addView\([^\n]*minecraftInstallProgress\(item\)[^\n]*\)\)',
            re.DOTALL,
        )
        match = pattern.search(s)
        if not match:
            # Support the Step 221/222 shape where the state line has not yet been created.
            anchor = '            val installed = MinecraftVersionInstallManager.isInstalled(this, item)'
            if anchor not in s:
                raise SystemExit('[step229] version selector install row not found')
            row_start = s.rfind('\n', 0, s.find(anchor)) + 1
            row_end = s.find('\n        }', s.find(anchor))
            if row_end < 0:
                row_end = s.find('\n            }', s.find(anchor))
            if row_end < 0:
                raise SystemExit('[step229] version selector row boundary not found')
            old = s[row_start:row_end]
            prefix = old.split('val installed', 1)[0]
            replacement = prefix + '''val state = MinecraftVersionInstallManager.state(this, item)\n            val installed = MinecraftVersionInstallManager.isInstalled(this, item)\n            val paused = state == MinecraftVersionInstallManager.State.FAILED &&\n                MinecraftVersionInstallManager.lastError(this, item) == "Installation cancelled"\n            val action = when {\n                installed -> button("Installed", true)\n                state == MinecraftVersionInstallManager.State.DOWNLOADING -> button("Cancel")\n                paused -> button("Resume")\n                else -> button("Install")\n            }\n            action.setOnClickListener {\n                when {\n                    installed -> { saveMinecraftVersion(item); showPage("Game") }\n                    state == MinecraftVersionInstallManager.State.DOWNLOADING -> cancelMinecraftVersionInstall(item)\n                    else -> installMinecraftVersion(item)\n                }\n            }\n            line.addView(action, LinearLayout.LayoutParams(dp(110), dp(46)))\n            info.addView(label("${state.name.replace('_', ' ')}  ·  ${minecraftInstallProgress(item)}", 11f, false))\n'''
            s = s[:row_start] + replacement + s[row_end:]
        else:
            block = match.group(0)
            if 'cancelMinecraftVersionInstall(item)' not in block:
                indent = match.group('indent')
                replacement = '''{i}val state = MinecraftVersionInstallManager.state(this, item)\n{i}val installed = MinecraftVersionInstallManager.isInstalled(this, item)\n{i}val paused = state == MinecraftVersionInstallManager.State.FAILED &&\n{i}    MinecraftVersionInstallManager.lastError(this, item) == "Installation cancelled"\n{i}val action = when {{\n{i}    installed -> button("Installed", true)\n{i}    state == MinecraftVersionInstallManager.State.DOWNLOADING -> button("Cancel")\n{i}    paused -> button("Resume")\n{i}    else -> button("Install")\n{i}}}\n{i}action.setOnClickListener {{\n{i}    when {{\n{i}        installed -> {{ saveMinecraftVersion(item); showPage("Game") }}\n{i}        state == MinecraftVersionInstallManager.State.DOWNLOADING -> cancelMinecraftVersionInstall(item)\n{i}        else -> installMinecraftVersion(item)\n{i}    }}\n{i}}}\n{i}line.addView(action, LinearLayout.LayoutParams(dp(110), dp(46)))\n{i}info.addView(label("${{state.name.replace('_', ' ')}}  ·  ${{minecraftInstallProgress(item)}}", 11f, false))'''.format(i=indent)
                s = s[:match.start()] + replacement + s[match.end():]

    ui.write_text(s, encoding='utf-8')
    print('[step229] live persisted installation status exposed in version UI')
    print('[step229] Cancel/Pause and Resume controls wired')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
