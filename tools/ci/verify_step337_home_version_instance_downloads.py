#!/usr/bin/env python3
"""Step 337: fail-closed verification for the final Home version/instance/download UI."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    manager = root / "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt"
    if not ui.is_file() or not manager.is_file():
        raise SystemExit("[step337] required launcher sources are missing")
    u = ui.read_text(encoding="utf-8")
    m = manager.read_text(encoding="utf-8")

    required_ui = (
        "// STEP334_SERVER_TOOLBAR_DELETE",
        "// STEP335_HOME_VERSION_INSTANCE_DOWNLOADS",
        "private fun openVersionSelector()",
        "private fun openInstanceSelector()",
        "private fun downloadCard(): LinearLayout",
        "private fun persistDownloadProgress(progress: MinecraftVersionInstallManager.Progress)",
        'getSharedPreferences(\"droid_launcher_downloads\", MODE_PRIVATE)',
        'Version  ·  ${selectedMinecraftVersion()}',
        'Instance  ·  ${selectedMinecraftProfile()}',
        'active_downloaded',
        'active_total',
        'active_stage',
        'active_state',
        '%.1f%%',
        'formatMiB(downloaded)',
        'formatMiB(total)',
        ' / ${if (total > 0L) formatMiB(total) else "? MB"}',
    )
    required_manager = (
        "fun installedVersions(context: Context): List<String>",
        "filter { isInstalled(context, it) }",
    )
    missing_ui = [x for x in required_ui if x not in u]
    missing_manager = [x for x in required_manager if x not in m]
    if missing_ui:
        raise SystemExit("[step337] missing Home UI contracts: " + ", ".join(missing_ui))
    if missing_manager:
        raise SystemExit("[step337] missing version inventory contracts: " + ", ".join(missing_manager))

    setup = u.find('val versionCard = cardView(16)')
    launch = u.find('val launch = button("Launch", true)')
    if setup < 0 or launch < 0 or setup > launch:
        raise SystemExit("[step337] Version/Instance setup is not above Launch")

    if u.count('private fun downloadCard(): LinearLayout {') != 1:
        raise SystemExit("[step337] downloadCard must have exactly one declaration")
    if u.count('private fun openVersionSelector()') != 1 or u.count('private fun openInstanceSelector()') != 1:
        raise SystemExit("[step337] selector helpers must each have exactly one declaration")

    print("[step337] Home Version selector contract verified")
    print("[step337] Home Instance selector contract verified")
    print("[step337] live download version/stage/percentage/MB contract verified")
    print("[step337] selector/download UI is confirmed above Launch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
