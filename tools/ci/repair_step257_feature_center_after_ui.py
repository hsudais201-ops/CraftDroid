#!/usr/bin/env python3
"""Final UI integrity pass: restore the Feature Center after later UI patch steps.

Several historical UI repair scripts replace the block between gamePage() and
rendererPage(). That can legitimately remove a method inserted earlier in the
pipeline while leaving its navigation call behind. This final pass makes the
Feature Center contract idempotent and ensures the generated activity compiles.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys

FEATURE_METHOD = r'''
    private fun featuresPage() {
        pageArea.addView(section("Feature Center", "Launcher tools, customization, content management and quality-of-life controls"))
        val groups = listOf(
            "Launcher & Instances" to listOf(
                "Instance profiles" to "Separate game setups with their own mods, worlds, packs and settings.",
                "Version manager" to "Stable releases, snapshots and installed-version health checks.",
                "Mod loader manager" to "Fabric, Forge, Quilt and compatible loader selection.",
                "Import / Export" to "Bring in launcher instances and export complete profiles for backup or transfer.",
                "Quick Play" to "Save one-tap shortcuts for favorite servers and worlds."
            ),
            "Content" to listOf(
                "Mod Browser" to "Find, install, update and disable supported mods.",
                "Modpack Browser" to "Install packs from supported indexes or local archives.",
                "Resource Packs" to "Install, activate, reorder and remove resource packs.",
                "Shader Packs" to "Install and switch shader profiles with renderer-aware presets.",
                "World Manager" to "Import, duplicate, back up, rename and remove worlds.",
                "Screenshots" to "Browse, rename, copy and share captured screenshots."
            ),
            "Accounts & Identity" to listOf(
                "Microsoft account" to "Primary authenticated account path for Minecraft Java ownership.",
                "Local test account" to "Safe local-only profile for launcher development and fixtures.",
                "Skin manager" to "Select and switch saved Java skins from the account area.",
                "Profile presets" to "Store per-account launcher preferences without mixing game profiles."
            ),
            "Servers & Multiplayer" to listOf(
                "Server manager" to "Multiple saved servers with selected-server launching.",
                "Live status" to "Online/offline status, latency and player information when available.",
                "Server details" to "Edit host, port, display name and quick launch preferences.",
                "Favorite servers" to "Pin the most-used servers near the top of the home screen."
            ),
            "Performance" to listOf(
                "Auto memory" to "Choose a safe JVM memory target based on detected device resources.",
                "Performance presets" to "Battery saver, balanced, quality and high-performance profiles.",
                "Renderer selection" to "Automatic graphics backend plus explicit renderer preferences.",
                "FPS-friendly settings" to "Resolution scaling and conservative graphics defaults for low-end devices.",
                "Launch diagnostics" to "Capture startup logs, crash summaries and launch metadata."
            ),
            "Customization" to listOf(
                "Launcher themes" to "Light, dark and premium custom color/background profiles.",
                "Landscape layout" to "Full-screen landscape-first interface with safe-area handling.",
                "Touch controls" to "Move, resize, recolor, hide, duplicate and remap every control independently.",
                "UI scale" to "Adjust launcher density for phones, tablets and Chromebook-sized displays.",
                "Accessibility" to "Text size, contrast-friendly presentation and reduced-motion options."
            ),
            "Maintenance & Safety" to listOf(
                "Download queue" to "Track installation jobs with retry, cancellation and progress reporting.",
                "Integrity checks" to "Validate downloaded version metadata and artifacts before launch.",
                "Offline mode" to "Keep installed profiles usable when network services are unavailable.",
                "Backup & restore" to "Protect worlds, settings, screenshots and launcher profiles.",
                "Logs & reports" to "Review launcher diagnostics without requiring an external debugger."
            ),
            "Advanced" to listOf(
                "Java runtime profiles" to "Bind Minecraft versions to compatible Java runtimes.",
                "Custom JVM arguments" to "Advanced launch arguments with validation before execution.",
                "Game directory tools" to "Open or inspect profile storage and managed files.",
                "Experimental features" to "Opt into development features without changing stable defaults."
            )
        )
        groups.forEach { (group, items) ->
            pageArea.addView(label(group, 17f, true).apply { setPadding(dp(12), dp(12), dp(12), dp(4)) })
            items.forEach { (name, description) -> featureToggle(name, description) }
        }
    }

    private fun featureToggle(name: String, description: String) {
        val prefs = getSharedPreferences("droid_features", MODE_PRIVATE)
        val key = "enabled_" + name.lowercase().replace("[^a-z0-9]+".toRegex(), "_")
        val row = cardView(12)
        val line = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        info.addView(label(name, 15f, true))
        info.addView(label(description, 12f))
        line.addView(info, LinearLayout.LayoutParams(0, -2, 1f))
        val toggle = android.widget.Switch(this).apply {
            isChecked = prefs.getBoolean(key, true)
            setOnCheckedChangeListener { _, checked -> prefs.edit().putBoolean(key, checked).apply() }
            contentDescription = "$name feature toggle"
        }
        line.addView(toggle, LinearLayout.LayoutParams(dp(56), dp(48)))
        row.addView(line)
        pageArea.addView(row)
    }
'''


def patch_show_page(source: str) -> str:
    if '"Features" -> featuresPage()' in source:
        return source
    match = re.search(r'(?m)^(\s*)"Game"\s*->\s*gamePage\(\)\s*$', source)
    if not match:
        raise SystemExit("[step257] showPage Game anchor not found")
    line = match.group(0)
    return source[:match.start()] + line + f'\n{match.group(1)}"Features" -> featuresPage()' + source[match.end():]


def patch_nav(source: str) -> str:
    if '"✦" to "Features"' in source or 'contentDescription = "Features - Feature Center"' in source:
        return source
    match = re.search(r'(?m)^(\s*)(.*"⌕"\s+to\s+"Search by ID",)(.*)$', source)
    if not match:
        # Later UI generators may already provide the real Features button as a
        # standalone View rather than the historical icon/page tuple. That is a
        # valid equivalent and must not be treated as corruption.
        if 'setOnClickListener { showPage("Features") }' in source and 'Features - Feature Center' in source:
            return source
        raise SystemExit("[step257] navigation Search by ID anchor not found")
    replacement = f'{match.group(1)}{match.group(2)} "✦" to "Features",{match.group(3)}'
    return source[:match.start()] + replacement + source[match.end():]


def patch_method(source: str) -> str:
    if 'private fun featuresPage()' in source:
        return source
    anchor = '    private fun rendererPage() {'
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit("[step257] rendererPage anchor not found")
    return source[:pos] + FEATURE_METHOD + '\n' + source[pos:]


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step257] UI source not found: {ui}")
    source = ui.read_text(encoding="utf-8")
    source = patch_show_page(source)
    source = patch_nav(source)
    source = patch_method(source)
    ui.write_text(source, encoding="utf-8")
    if '"Features" -> featuresPage()' not in source or 'private fun featuresPage()' not in source:
        raise SystemExit("[step257] Feature Center integrity verification failed")
    if '"✦" to "Features"' not in source and not ('Features - Feature Center' in source and 'setOnClickListener { showPage("Features") }' in source):
        raise SystemExit("[step257] Feature Center navigation handler missing")
    print(f"[step257] Feature Center restored and verified: {ui}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
