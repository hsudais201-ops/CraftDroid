#!/usr/bin/env python3
"""Step 222: connect the real Minecraft version installer to the Droid Launcher UI."""
from pathlib import Path
import sys


def replace_function(src: str, signature: str, next_signature: str, replacement: str) -> str:
    start = src.find(signature)
    end = src.find(next_signature, start)
    if start < 0 or end < 0:
        raise SystemExit(f"[step222] function anchors not found: {signature} -> {next_signature}")
    return src[:start] + replacement + src[end:]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step222] missing UI source: {ui}")

    s = ui.read_text(encoding="utf-8")

    helper = r'''    private fun installMinecraftVersion(version: String) {
        val status = Toast.makeText(this, "Preparing Minecraft $version…", Toast.LENGTH_SHORT)
        status.show()
        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {
            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                runOnUiThread {
                    val pct = if (progress.total > 0L) ((progress.downloaded * 100L) / progress.total).toInt().coerceIn(0, 100) else 0
                    setTitle("$version · ${progress.stage} · $pct%")
                }
            }

            override fun onComplete(version: String) {
                saveMinecraftVersion(version)
                runOnUiThread {
                    Toast.makeText(this@DroidLauncherUiActivity, "Minecraft $version installed", Toast.LENGTH_LONG).show()
                    showPage("Search by ID")
                }
            }

            override fun onError(version: String, error: Throwable) {
                runOnUiThread {
                    Toast.makeText(this@DroidLauncherUiActivity, "Install failed: ${error.message ?: "unknown error"}", Toast.LENGTH_LONG).show()
                    showPage("Search by ID")
                }
            }
        })
    }

'''
    if 'private fun installMinecraftVersion(version: String)' not in s:
        anchor = '    private fun rendererPage() {'
        if anchor not in s:
            raise SystemExit('[step222] rendererPage anchor not found')
        s = s.replace(anchor, helper + anchor, 1)

    # Rebuild the Game page so Play is gated by the real installed state.
    game = r'''    private fun gamePage() {
        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
        val java = getResolvedJavaForLaunch(version)
        val installed = MinecraftVersionInstallManager.isInstalled(this, version)
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }

        val left = cardView(18)
        left.addView(label("Minecraft profile", 17f, true))
        left.addView(label(profile, 20f, true))
        left.addView(label("Version  ·  $version", 13f, false))
        left.addView(label("Java  ·  $java", 13f, false))
        left.addView(label(if (installed) "Ready to launch" else "Version not installed", 13f, installed))
        val versionButton = button("Choose Version")
        versionButton.setOnClickListener { showPage("Search by ID") }
        left.addView(versionButton, LinearLayout.LayoutParams(-1, dp(46)))
        row.addView(left, LinearLayout.LayoutParams(0, -1, 1f))

        val right = cardView(18)
        right.gravity = Gravity.CENTER
        right.addView(label("Minecraft Java Edition", 20f, true))
        right.addView(label("$version  ·  $profile", 14f, true))
        right.addView(label("Java $java", 13f, false))
        val launch = button(if (installed) "▶  PLAY" else "↓  INSTALL", true)
        launch.setOnClickListener {
            if (MinecraftVersionInstallManager.isInstalled(this, version)) {
                launchSelectedMinecraft()
            } else {
                installMinecraftVersion(version)
            }
        }
        right.addView(launch, LinearLayout.LayoutParams(-1, dp(56)))
        row.addView(right, LinearLayout.LayoutParams(dp(330), -1))
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360)))
    }

'''
    s = replace_function(s, '    private fun gamePage() {', '    private fun rendererPage() {', game)

    # Rebuild version cards with persistent installation state and Install/Play actions.
    library = r'''    private fun libraryPage(page: String) {
        if (page != "Search by ID") {
            pageArea.addView(section("Download · $page", "Modern launcher-style library browser"))
            val items = when (page) {
                "Saves" -> listOf("Survival World", "Creative Test", "Skyblock Backup")
                else -> listOf("26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9")
            }
            items.forEach { item ->
                val c = cardView(12)
                val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
                line.addView(label("▣", 22f), LinearLayout.LayoutParams(dp(34), dp(48)))
                val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
                info.addView(label(item, 16f, true))
                info.addView(label(if (page == "Saves") "Managed save" else "Managed item · Profile storage", 12f))
                line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
                line.addView(button(if (page == "Saves") "Import" else "Install"))
                c.addView(line)
                pageArea.addView(c)
            }
            return
        }

        pageArea.addView(section("Minecraft Versions", "Official Mojang versions · install once, resume downloads automatically"))
        val versions = listOf("1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4", "1.18.2", "1.16.5")
        val selected = selectedMinecraftVersion()
        versions.forEach { item ->
            val c = cardView(12)
            val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
            val installed = MinecraftVersionInstallManager.isInstalled(this, item)
            val state = MinecraftVersionInstallManager.state(this, item)
            val indicator = when {
                installed -> "✓"
                state == MinecraftVersionInstallManager.State.DOWNLOADING -> "↓"
                state == MinecraftVersionInstallManager.State.FAILED -> "!"
                item == selected -> "○"
                else -> "·"
            }
            line.addView(label(indicator, 24f), LinearLayout.LayoutParams(dp(38), dp(52)))
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            info.addView(label(item, 17f, true))
            val java = getResolvedJavaForLaunch(item)
            val detail = when {
                installed -> "Installed · Java $java"
                state == MinecraftVersionInstallManager.State.FAILED -> "Install failed · tap to retry"
                else -> "Not installed · Java $java"
            }
            info.addView(label(detail, 12f))
            line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))

            val action = button(when {
                installed && item == selected -> "PLAY"
                installed -> "SELECT"
                state == MinecraftVersionInstallManager.State.DOWNLOADING -> "RESUME"
                else -> "INSTALL"
            }, installed && item == selected)
            action.setOnClickListener {
                when {
                    installed -> {
                        saveMinecraftVersion(item)
                        showPage("Game")
                    }
                    else -> {
                        saveMinecraftVersion(item)
                        installMinecraftVersion(item)
                    }
                }
            }
            line.addView(action, LinearLayout.LayoutParams(dp(112), dp(46)))
            c.addView(line)
            pageArea.addView(c)
        }

        val profile = cardView(12)
        profile.addView(label("Profile", 16f, true))
        profile.addView(label("${selectedMinecraftProfile()}  ·  persistent launch profile", 12f, false))
        val profileLine = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        listOf("Default", "Survival", "PvP", "Modded").forEach { name ->
            val b = button(name, name == selectedMinecraftProfile())
            b.setOnClickListener { saveMinecraftProfile(name); showPage("Search by ID") }
            profileLine.addView(b, LinearLayout.LayoutParams(0, dp(44), 1f))
        }
        profile.addView(profileLine)
        pageArea.addView(profile)
    }

'''
    s = replace_function(s, '    private fun libraryPage(page: String) {', '    private fun aboutPage() {', library)

    ui.write_text(s, encoding="utf-8")
    print('[step222] real Minecraft installer wired to version selector')
    print('[step222] Game Play is blocked until selected version is installed')
    print('[step222] version cards expose persistent Install/Select/Play actions')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
