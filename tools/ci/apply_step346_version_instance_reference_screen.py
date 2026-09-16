#!/usr/bin/env python3
"""Step 346: add a dedicated Version & Instances screen.

The Home Version and Instance selectors open one shared management screen.  A visible
+ action on that screen opens the existing Step341 Game download/version manager.
"""
from pathlib import Path
import sys

MARKER = "// STEP346_VERSION_INSTANCE_REFERENCE_SCREEN"
UI_REL = Path("app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt")


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step346] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def method_block(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[step346] method not found: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[step346] opening brace not found: {signature}")
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
    raise SystemExit(f"[step346] unterminated method: {signature}")


PAGE = r'''    private fun showVersionInstancesPage() {
        // STEP346_VERSION_INSTANCE_REFERENCE_SCREEN
        title.text = "Version / Instances"
        pageArea.removeAllViews()

        val topRow = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(6), dp(4), dp(6), dp(8))
        }
        val back = button("⌂")
        back.contentDescription = "Home"
        back.setOnClickListener { showPage("Game") }
        topRow.addView(back, LinearLayout.LayoutParams(dp(56), dp(48)))

        val heading = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12), 0, dp(12), 0)
        }
        heading.addView(label("Versions & Instances", 17f, true))
        heading.addView(label("Choose what to launch, or add a new version", 11f, false))
        topRow.addView(heading, LinearLayout.LayoutParams(0, dp(52), 1f))

        val add = button("+")
        add.textSize = 23f
        add.contentDescription = "Add version or instance"
        add.setOnClickListener {
            // Reuse the existing Step341 download/version area instead of duplicating it.
            libraryPage("Game")
        }
        topRow.addView(add, LinearLayout.LayoutParams(dp(64), dp(52)))
        pageArea.addView(topRow)

        val active = roundedCard(16)
        active.addView(label("Active launch setup", 14f, true))
        active.addView(label("Version  ·  ${selectedMinecraftVersion()}", 13f, true))
        active.addView(label("Instance  ·  ${selectedMinecraftProfile()}", 13f, true))
        pageArea.addView(active)

        val versionSection = roundedCard(16)
        versionSection.addView(label("Installed Versions", 14f, true))
        val versions = (installedMinecraftVersionsForUi() + listOf(selectedMinecraftVersion())).distinct()
        versions.forEach { version ->
            val row = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(8), dp(4), dp(8), dp(4))
            }
            row.addView(label(version, 14f, version == selectedMinecraftVersion()), LinearLayout.LayoutParams(0, dp(48), 1f))
            val choose = button(if (version == selectedMinecraftVersion()) "Selected" else "Use")
            choose.isAllCaps = false
            choose.contentDescription = "Use Minecraft $version"
            choose.setOnClickListener {
                saveMinecraftVersion(version)
                showVersionInstancesPage()
            }
            row.addView(choose, LinearLayout.LayoutParams(dp(96), dp(46)))
            versionSection.addView(row)
        }
        pageArea.addView(versionSection)

        val instanceSection = roundedCard(16)
        instanceSection.addView(label("Instances", 14f, true))
        listOf("Default", "Survival", "PvP", "Modded").forEach { instance ->
            val row = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(8), dp(4), dp(8), dp(4))
            }
            row.addView(label(instance, 14f, instance == selectedMinecraftProfile()), LinearLayout.LayoutParams(0, dp(48), 1f))
            val choose = button(if (instance == selectedMinecraftProfile()) "Selected" else "Use")
            choose.isAllCaps = false
            choose.contentDescription = "Use $instance instance"
            choose.setOnClickListener {
                saveMinecraftProfile(instance)
                showVersionInstancesPage()
            }
            row.addView(choose, LinearLayout.LayoutParams(dp(96), dp(46)))
            instanceSection.addView(row)
        }
        pageArea.addView(instanceSection)

        val hint = roundedCard(16)
        hint.addView(label("+ Add", 14f, true))
        hint.addView(label("Tap + to open the version download/install area.", 12f, false))
        pageArea.addView(hint)
    }

'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")
    if MARKER not in source:
        anchor = '    private fun openVersionSelector() {'
        if anchor not in source:
            raise SystemExit("[step346] openVersionSelector anchor not found")
        source = source.replace(anchor, PAGE + anchor, 1)

    source = source.replace(
        'versionButton.setOnClickListener { openVersionSelector() }',
        'versionButton.setOnClickListener { showVersionInstancesPage() }',
    )
    source = source.replace(
        'instanceButton.setOnClickListener { openInstanceSelector() }',
        'instanceButton.setOnClickListener { showVersionInstancesPage() }',
    )

    if 'versionButton.setOnClickListener { showVersionInstancesPage() }' not in source:
        raise SystemExit("[step346] Home Version click contract not installed")
    if 'instanceButton.setOnClickListener { showVersionInstancesPage() }' not in source:
        raise SystemExit("[step346] Home Instance click contract not installed")
    if 'add.contentDescription = "Add version or instance"' not in source:
        raise SystemExit("[step346] plus action contract missing")
    if 'add.setOnClickListener {' not in source or 'libraryPage("Game")' not in source:
        raise SystemExit("[step346] plus-to-download contract missing")
    if source.count('private fun showVersionInstancesPage()') != 1:
        raise SystemExit("[step346] showVersionInstancesPage declaration count is not exactly one")

    ui.write_text(source, encoding="utf-8")
    print("[step346] Version / Instances reference screen installed")
    print("[step346] Home Version and Instance now open the shared screen")
    print("[step346] + opens the existing Step341 Game download/version manager")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
