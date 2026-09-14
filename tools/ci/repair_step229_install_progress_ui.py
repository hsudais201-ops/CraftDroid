#!/usr/bin/env python3
"""Step 229: expose live install progress plus cancel/resume controls in the launcher UI."""
from pathlib import Path
import sys


def replace_once(text: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if old not in text:
        return text, False
    return text.replace(old, new, 1), True


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / 'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.exists():
        raise SystemExit(f'[step229] missing UI source: {ui}')
    s = ui.read_text(encoding='utf-8')

    # Upgrade the existing Step 223/222 progress helper.
    old_helper = '''    private fun minecraftInstallProgress(version: String): String {\n        return when (MinecraftVersionInstallManager.state(this, version)) {\n            MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"\n            MinecraftVersionInstallManager.State.DOWNLOADING -> "Downloading…"\n            MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"\n            MinecraftVersionInstallManager.State.NOT_INSTALLED -> "Ready to install"\n        }\n    }\n'''
    new_helper = '''    private fun minecraftInstallProgress(version: String): String {\n        val progress = MinecraftVersionInstallManager.savedProgress(this, version)\n        val state = MinecraftVersionInstallManager.state(this, version)\n        val percent = if (progress.total > 0L) ((progress.downloaded * 100L) / progress.total).coerceIn(0L, 100L) else null\n        return when {\n            state == MinecraftVersionInstallManager.State.INSTALLED -> "Ready to play"\n            state == MinecraftVersionInstallManager.State.DOWNLOADING && percent != null -> "${percent}% · ${progress.stage}"\n            state == MinecraftVersionInstallManager.State.DOWNLOADING -> progress.stage\n            state == MinecraftVersionInstallManager.State.FAILED && MinecraftVersionInstallManager.lastError(this, version) == "Installation cancelled" -> "Paused · tap Resume"\n            state == MinecraftVersionInstallManager.State.FAILED -> "Failed · tap Install to retry"\n            else -> "Ready to install"\n        }\n    }\n'''
    if old_helper in s:
        s = s.replace(old_helper, new_helper, 1)
    elif 'savedProgress(this, version)' not in s:
        raise SystemExit('[step229] install-progress helper not found')

    # Upgrade install error handling and add a real cancel action.
    if 'private fun cancelMinecraftVersionInstall(version: String)' not in s:
        anchor = '    private fun rendererPage() {'
        if anchor not in s:
            raise SystemExit('[step229] rendererPage anchor not found for cancel helper')
        helper = '''    private fun cancelMinecraftVersionInstall(version: String) {\n        MinecraftVersionInstallManager.cancel(this, version)\n        Toast.makeText(this, "Minecraft $version installation paused", Toast.LENGTH_SHORT).show()\n        showPage("Search by ID")\n    }\n\n'''
        s = s.replace(anchor, helper + anchor, 1)

    # The actual Step 222 version-card action row uses this exact decision tree.
    old_action = '''            val action = button(when {\n                installed && item == selected -> "PLAY"\n                installed -> "SELECT"\n                state == MinecraftVersionInstallManager.State.DOWNLOADING -> "RESUME"\n                else -> "INSTALL"\n            }, installed && item == selected)\n            action.setOnClickListener {\n                when {\n                    installed -> {\n                        saveMinecraftVersion(item)\n                        showPage("Game")\n                    }\n                    else -> {\n                        saveMinecraftVersion(item)\n                        installMinecraftVersion(item)\n                    }\n                }\n            }\n            line.addView(action, LinearLayout.LayoutParams(dp(112), dp(46)))\n'''
    new_action = '''            val paused = state == MinecraftVersionInstallManager.State.FAILED &&\n                MinecraftVersionInstallManager.lastError(this, item) == "Installation cancelled"\n            val action = button(when {\n                installed && item == selected -> "PLAY"\n                installed -> "SELECT"\n                state == MinecraftVersionInstallManager.State.DOWNLOADING -> "CANCEL"\n                paused -> "RESUME"\n                else -> "INSTALL"\n            }, installed && item == selected)\n            action.setOnClickListener {\n                when {\n                    installed -> {\n                        saveMinecraftVersion(item)\n                        showPage("Game")\n                    }\n                    state == MinecraftVersionInstallManager.State.DOWNLOADING -> cancelMinecraftVersionInstall(item)\n                    else -> {\n                        saveMinecraftVersion(item)\n                        installMinecraftVersion(item)\n                    }\n                }\n            }\n            line.addView(action, LinearLayout.LayoutParams(dp(112), dp(46)))\n'''
    if old_action in s:
        s = s.replace(old_action, new_action, 1)
    elif 'cancelMinecraftVersionInstall(item)' not in s:
        raise SystemExit('[step229] actual version-card action row not found')

    # Add live progress text immediately after the version detail label.
    marker = '''            info.addView(label(detail, 12f))\n'''
    replacement = marker + '''            info.addView(label("${state.name.replace('_', ' ')}  ·  ${minecraftInstallProgress(item)}", 11f, false))\n'''
    if 'minecraftInstallProgress(item)' not in s:
        if marker not in s:
            raise SystemExit('[step229] version detail label anchor not found')
        s = s.replace(marker, replacement, 1)

    ui.write_text(s, encoding='utf-8')
    print('[step229] live persisted installation status exposed in version UI')
    print('[step229] Cancel/Pause and Resume controls wired')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
