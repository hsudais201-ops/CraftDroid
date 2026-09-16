#!/usr/bin/env python3
"""Step 335: expose installed Minecraft versions/instances and live download progress on Home.

The generated Home page gets a compact selector directly above Launch.  The installer
also persists live byte progress so the Home card can show the active version, item name,
percentage, and downloaded/total MB without pretending that a download is complete.
"""
from pathlib import Path
import re
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step335] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step335] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step335] method opening brace not found: {signature}")
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(source)):
        ch = source[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit(f"[step335] unterminated method: {signature}")


def replace_method(source: str, signature: str, replacement: str) -> str:
    start, end = method_block(source, signature)
    return source[:start] + replacement + source[end:]


def replace_install_helper(source: str) -> str:
    signature = '    private fun installMinecraftVersion(version: String) {'
    if signature not in source:
        raise SystemExit('[step335] installMinecraftVersion helper missing')
    helper = r'''    private fun persistDownloadProgress(progress: MinecraftVersionInstallManager.Progress) {
        getSharedPreferences("droid_launcher_downloads", MODE_PRIVATE).edit()
            .putString("active_version", progress.version)
            .putString("active_stage", progress.stage)
            .putLong("active_downloaded", progress.downloaded.coerceAtLeast(0L))
            .putLong("active_total", progress.total)
            .putString("active_state", progress.state.name)
            .apply()
    }

    private fun clearDownloadProgress(version: String, state: String) {
        val prefs = getSharedPreferences("droid_launcher_downloads", MODE_PRIVATE)
        if (prefs.getString("active_version", null) == version) {
            prefs.edit()
                .putString("active_state", state)
                .putString("active_stage", if (state == "INSTALLED") "Download complete" else prefs.getString("active_stage", "") ?: "")
                .apply()
        }
    }

    private fun installMinecraftVersion(version: String) {
        saveMinecraftVersion(version)
        persistDownloadProgress(
            MinecraftVersionInstallManager.Progress(
                version = version,
                downloaded = 0L,
                total = 0L,
                stage = "Starting download",
                state = MinecraftVersionInstallManager.State.DOWNLOADING
            )
        )
        Toast.makeText(this, "Downloading Minecraft $version…", Toast.LENGTH_SHORT).show()
        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {
            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                persistDownloadProgress(progress)
                runOnUiThread {
                    if (currentPage == "Game") showPage("Game")
                    else if (currentPage == "Search by ID") showPage("Search by ID")
                }
            }

            override fun onComplete(version: String) {
                clearDownloadProgress(version, "INSTALLED")
                runOnUiThread {
                    Toast.makeText(this@DroidLauncherUiActivity, "Minecraft $version installed", Toast.LENGTH_LONG).show()
                    showPage("Game")
                }
            }

            override fun onError(version: String, error: Throwable) {
                clearDownloadProgress(version, "FAILED")
                getSharedPreferences("droid_launcher_downloads", MODE_PRIVATE).edit()
                    .putString("active_stage", "Download failed: ${error.message ?: "unknown error"}")
                    .apply()
                runOnUiThread {
                    Toast.makeText(
                        this@DroidLauncherUiActivity,
                        "Install failed: ${error.message ?: "unknown error"}",
                        Toast.LENGTH_LONG
                    ).show()
                    showPage("Game")
                }
            }
        })
    }
'''
    return replace_method(source, signature, helper)


def selector_dialogs(source: str) -> str:
    marker = '    private fun accountAvatar(parent: LinearLayout, value: String) {'
    if marker not in source:
        raise SystemExit('[step335] accountAvatar anchor not found')
    helpers = r'''    private fun installedMinecraftVersionsForUi(): List<String> {
        return runCatching { MinecraftVersionInstallManager.installedVersions(this) }
            .getOrDefault(emptyList())
            .sortedWith(compareByDescending<String> { it.count { ch -> ch == '.' } }.thenByDescending { it })
    }

    private fun openVersionSelector() {
        val installed = installedMinecraftVersionsForUi()
        val candidates = (installed + listOf("1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4", "1.18.2", "1.16.5"))
            .distinct()
        val checked = candidates.indexOf(selectedMinecraftVersion()).coerceAtLeast(0)
        android.app.AlertDialog.Builder(this)
            .setTitle("Select Minecraft version")
            .setSingleChoiceItems(candidates.toTypedArray(), checked) { dialog, which ->
                saveMinecraftVersion(candidates[which])
                dialog.dismiss()
                showPage("Game")
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun openInstanceSelector() {
        val prefs = getSharedPreferences("droid_launcher", MODE_PRIVATE)
        val names = listOf("Default", "Survival", "PvP", "Modded")
        val checked = names.indexOf(selectedMinecraftProfile()).coerceAtLeast(0)
        android.app.AlertDialog.Builder(this)
            .setTitle("Select launcher instance")
            .setSingleChoiceItems(names.toTypedArray(), checked) { dialog, which ->
                saveMinecraftProfile(names[which])
                dialog.dismiss()
                showPage("Game")
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun formatMiB(bytes: Long): String =
        "%.1f MB".format(java.util.Locale.US, bytes.coerceAtLeast(0L) / 1048576.0)

    private fun downloadCard(): LinearLayout {
        val card = cardView(16)
        val prefs = getSharedPreferences("droid_launcher_downloads", MODE_PRIVATE)
        val version = prefs.getString("active_version", null)
        val state = prefs.getString("active_state", "") ?: ""
        val stage = prefs.getString("active_stage", "") ?: ""
        val downloaded = prefs.getLong("active_downloaded", 0L).coerceAtLeast(0L)
        val total = prefs.getLong("active_total", 0L)
        val downloading = state == MinecraftVersionInstallManager.State.DOWNLOADING.name
        val failed = state == MinecraftVersionInstallManager.State.FAILED.name
        val title = when {
            downloading && !version.isNullOrBlank() -> "Downloading · $version"
            failed && !version.isNullOrBlank() -> "Download failed · $version"
            state == MinecraftVersionInstallManager.State.INSTALLED.name && !version.isNullOrBlank() -> "Ready · $version"
            else -> "Downloads"
        }
        card.addView(label(title, 15f, true))
        if (!version.isNullOrBlank() && (downloading || failed || state == MinecraftVersionInstallManager.State.INSTALLED.name)) {
            val percent = if (total > 0L) ((downloaded.toDouble() / total.toDouble()) * 100.0).coerceIn(0.0, 100.0) else 0.0
            val pctText = if (downloading && total <= 0L) "Preparing…" else "%.1f%%".format(java.util.Locale.US, percent)
            card.addView(label(stage.ifBlank { "Minecraft $version" }, 11f, false))
            card.addView(label("$pctText  ·  ${formatMiB(downloaded)} / ${if (total > 0L) formatMiB(total) else "? MB"}", 12f, true))
            if (downloading) {
                val bar = android.widget.ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal)
                bar.max = 1000
                bar.progress = (percent * 10.0).toInt().coerceIn(0, 1000)
                card.addView(bar, LinearLayout.LayoutParams(-1, dp(10)))
            }
        } else {
            card.addView(label("No active downloads", 11f, false))
        }
        return card
    }

'''
    return source.replace(marker, helpers + marker, 1)


def replace_home(source: str) -> str:
    signature = '    private fun homePage() {'
    start, end = method_block(source, signature)
    old = source[start:end]
    # Preserve the existing page's server/account content but replace only the launch area
    # with a version/instance/download stack directly above the Launch button.
    needle = '''        val launch = button("Launch", true)
        launch.textSize = 18f
        launch.setOnClickListener {
            if (selectedAccountIndex() < 0) showPage("Accounts") else launchSelectedMinecraft()
        }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(68)).apply { topMargin = dp(10) })
'''
    if needle not in old:
        raise SystemExit('[step335] expected launch block not found in homePage')
    replacement = '''        val versionCard = cardView(16)
        versionCard.addView(label("Launch setup", 16f, true))
        val versionButton = button("Version  ·  ${selectedMinecraftVersion()}", true)
        versionButton.setOnClickListener { openVersionSelector() }
        versionCard.addView(versionButton, LinearLayout.LayoutParams(-1, dp(46)))
        val instanceButton = button("Instance  ·  ${selectedMinecraftProfile()}")
        instanceButton.setOnClickListener { openInstanceSelector() }
        versionCard.addView(instanceButton, LinearLayout.LayoutParams(-1, dp(46)))
        right.addView(versionCard, LinearLayout.LayoutParams(-1, dp(0), 0f))
        right.addView(downloadCard(), LinearLayout.LayoutParams(-1, dp(0), 0f).apply { topMargin = dp(8) })

        val launch = button("Launch", true)
        launch.textSize = 18f
        launch.setOnClickListener {
            if (selectedAccountIndex() < 0) showPage("Accounts") else launchSelectedMinecraft()
        }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(68)).apply { topMargin = dp(10) })
'''
    # Use wrap-content for the two cards: dp(0) + weight 0 is invalid-looking, so build with WRAP_CONTENT explicitly.
    replacement = replacement.replace('LinearLayout.LayoutParams(-1, dp(0), 0f)', 'LinearLayout.LayoutParams(-1, LinearLayout.LayoutParams.WRAP_CONTENT)')
    source = source[:start] + old.replace(needle, replacement, 1) + source[end:]
    return source


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")
    if 'private fun persistDownloadProgress(progress: MinecraftVersionInstallManager.Progress)' not in source:
        source = replace_install_helper(source)
    if 'private fun installedMinecraftVersionsForUi(): List<String>' not in source:
        source = selector_dialogs(source)
    source = replace_home(source)
    if source.count('    private fun downloadCard(): LinearLayout {') != 1:
        raise SystemExit('[step335] downloadCard declaration count is not exactly one')
    if 'Version  ·  ${selectedMinecraftVersion()}' not in source:
        raise SystemExit('[step335] version selector did not land in Home')
    if 'Instance  ·  ${selectedMinecraftProfile()}' not in source:
        raise SystemExit('[step335] instance selector did not land in Home')
    if 'STEP335_HOME_VERSION_INSTANCE_DOWNLOADS' not in source:
        source += '\n    // STEP335_HOME_VERSION_INSTANCE_DOWNLOADS\n'
    ui.write_text(source, encoding="utf-8")
    print('[step335] Home now exposes Version and Instance above Launch')
    print('[step335] live download card persists version, stage, percentage and MB progress')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
