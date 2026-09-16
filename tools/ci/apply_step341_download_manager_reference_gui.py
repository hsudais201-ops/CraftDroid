#!/usr/bin/env python3
"""Step 341: build the install/version manager from the supplied 3.jpeg reference."""
from pathlib import Path
import re
import sys

MARKER = "// STEP341_DOWNLOAD_MANAGER_REFERENCE_GUI"

METHODS = r'''    private fun libraryPage(page: String) {
        // STEP341_DOWNLOAD_MANAGER_REFERENCE_GUI
        val titleName = when (page) {
            "Game" -> "Game"
            "Modpack" -> "Modpack"
            "Mod" -> "Mod"
            "Resource Pack" -> "Resource Pack"
            "Shader Pack" -> "Shader Pack"
            else -> page
        }
        title.text = "Download - $titleName"
        pageArea.removeAllViews()

        val filterRow = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(4), dp(2), dp(4), dp(4))
        }
        listOf("✓  Release", "Snapshot", "April Fools", "Old Versions").forEachIndexed { index, textValue ->
            val chip = button(textValue, index == 0)
            chip.textSize = 12f
            chip.setOnClickListener { showDownloadCategoryDialog(titleName, textValue) }
            filterRow.addView(chip, LinearLayout.LayoutParams(dp(if (index == 2) 130 else 112), dp(46)).apply {
                setMargins(dp(2), 0, dp(4), 0)
            })
        }
        val search = android.widget.EditText(this).apply {
            hint = "Search"
            isSingleLine = true
            textSize = 13f
            setPadding(dp(14), 0, dp(14), 0)
            background = android.graphics.drawable.GradientDrawable().apply {
                setColor(Color.rgb(250, 250, 250))
                cornerRadius = dp(16).toFloat()
                setStroke(dp(1), Color.rgb(232, 233, 235))
            }
        }
        filterRow.addView(search, LinearLayout.LayoutParams(0, dp(46), 1f).apply {
            setMargins(dp(4), 0, dp(4), 0)
        })
        val refresh = button("↻")
        refresh.contentDescription = "Refresh $titleName download list"
        refresh.setOnClickListener {
            android.widget.Toast.makeText(this, "Refreshing $titleName list", android.widget.Toast.LENGTH_SHORT).show()
        }
        filterRow.addView(refresh, LinearLayout.LayoutParams(dp(48), dp(46)))
        pageArea.addView(filterRow)

        if (page != "Game") {
            val managerCard = roundedCard(16)
            val managerBox = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(12), dp(6), dp(12), dp(6))
            }
            managerBox.addView(label("Minecraft version", 13f, true), LinearLayout.LayoutParams(dp(145), dp(48)))
            val versionButton = button(selectedMinecraftVersion)
            versionButton.contentDescription = "Select Minecraft version for $titleName"
            versionButton.setOnClickListener { showVersionSelectionDialog(titleName) }
            managerBox.addView(versionButton, LinearLayout.LayoutParams(0, dp(48), 1f))
            val loaderButton = button(selectedLoader)
            loaderButton.contentDescription = "Select loader for $titleName"
            loaderButton.setOnClickListener { showLoaderSelectionDialog(titleName) }
            managerBox.addView(loaderButton, LinearLayout.LayoutParams(dp(138), dp(48)))
            managerCard.addView(managerBox)
            pageArea.addView(managerCard)

            val optiCard = roundedCard(16)
            val optiBox = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(12), dp(4), dp(12), dp(4))
            }
            optiBox.addView(label("OptiFine", 14f, true), LinearLayout.LayoutParams(0, dp(48), 1f))
            val opti = android.widget.CheckBox(this).apply {
                text = "Enable"
                isChecked = optiFineEnabled
                setOnCheckedChangeListener { _, checked ->
                    optiFineEnabled = checked
                    android.widget.Toast.makeText(this@DroidLauncherUiActivity, if (checked) "OptiFine enabled" else "OptiFine disabled", android.widget.Toast.LENGTH_SHORT).show()
                }
            }
            optiBox.addView(opti, LinearLayout.LayoutParams(dp(120), dp(48)))
            optiCard.addView(optiBox)
            pageArea.addView(optiCard)
        }

        val entries = when (page) {
            "Game" -> listOf(
                "26.2" to "Jun 16, 2026, 12:03:33 pm",
                "26.1.2" to "Apr 9, 2026, 10:12:23 am",
                "26.1.1" to "Apr 1, 2026, 9:06:36 am",
                "26.1" to "Mar 24, 2026, 12:11:04 pm",
                "1.21.11" to "Dec 9, 2025, 12:23:30 pm",
                "1.21.10" to "Oct 7, 2025, 9:17:23 am",
                "1.21.9" to "Sept 36, 2025, 11:58:43 am"
            )
            "Modpack" -> listOf("SkyFactory", "All the Mods", "Better Minecraft", "Create: Perfect World")
            "Mod" -> listOf("Sodium", "Lithium", "Fabric API", "Iris Shaders", "JourneyMap")
            "Resource Pack" -> listOf("Faithful", "Bare Bones", "Stay True", "Vanilla Tweaks")
            "Shader Pack" -> listOf("Complementary", "BSL", "Sildur's Vibrant", "MakeUp - Ultra Fast")
            else -> emptyList()
        }

        entries.forEach { (name, detail) ->
            val c = roundedCard(16)
            val row = LinearLayout(this).apply {
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(10), dp(5), dp(10), dp(5))
            }
            val icon = label(if (page == "Game") "▣" else "◇", 24f, false).apply { gravity = Gravity.CENTER }
            row.addView(icon, LinearLayout.LayoutParams(dp(60), dp(58)))
            val info = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            info.addView(label(if (page == "Game") "$name  Release" else name, 15f, true))
            info.addView(label(if (page == "Game") detail else "$selectedLoader · $selectedMinecraftVersion", 12f))
            row.addView(info, LinearLayout.LayoutParams(0, dp(64), 1f))
            val action = button(if (page == "Game") "↪" else "Install")
            action.contentDescription = if (page == "Game") "Select $name" else "Install $name"
            action.setOnClickListener {
                if (page == "Game") {
                    selectedMinecraftVersion = name
                    android.widget.Toast.makeText(this, "Selected Minecraft $name", android.widget.Toast.LENGTH_SHORT).show()
                    libraryPage(page)
                } else {
                    android.widget.Toast.makeText(this, "Installing $name for $selectedMinecraftVersion with $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()
                }
            }
            row.addView(action, LinearLayout.LayoutParams(dp(if (page == "Game") 64 else 94), dp(58)))
            c.addView(row)
            pageArea.addView(c)
        }
    }

    private var selectedMinecraftVersion: String = "26.2"
    private var selectedLoader: String = "Fabric"
    private var optiFineEnabled: Boolean = false

    private fun showVersionSelectionDialog(pageName: String) {
        val versions = arrayOf("26.2", "26.1.2", "26.1.1", "26.1", "1.21.11", "1.21.10", "1.21.9", "1.20.6", "1.20.4")
        android.app.AlertDialog.Builder(this)
            .setTitle("Select Minecraft version")
            .setSingleChoiceItems(versions, versions.indexOf(selectedMinecraftVersion).coerceAtLeast(0)) { dialog, which ->
                selectedMinecraftVersion = versions[which]
                android.widget.Toast.makeText(this, "$pageName · Minecraft $selectedMinecraftVersion", android.widget.Toast.LENGTH_SHORT).show()
                dialog.dismiss()
                libraryPage(pageName)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showLoaderSelectionDialog(pageName: String) {
        val loaders = arrayOf("Fabric", "Forge", "NeoForge", "Quilt", "OptiFine")
        android.app.AlertDialog.Builder(this)
            .setTitle("Select loader")
            .setSingleChoiceItems(loaders, loaders.indexOf(selectedLoader).coerceAtLeast(0)) { dialog, which ->
                selectedLoader = loaders[which]
                if (selectedLoader == "OptiFine") optiFineEnabled = true
                android.widget.Toast.makeText(this, "$pageName · loader $selectedLoader", android.widget.Toast.LENGTH_SHORT).show()
                dialog.dismiss()
                libraryPage(pageName)
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    private fun showDownloadCategoryDialog(pageName: String, category: String) {
        android.widget.Toast.makeText(this, "$pageName · $category", android.widget.Toast.LENGTH_SHORT).show()
    }

'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step341] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step341] download manager reference GUI already present")
        return 0
    boundary = re.compile(r"    private fun libraryPage\(page: String\) \{[\s\S]*?\n    \}\n\n    private fun aboutPage\(\)", re.M)
    if not boundary.search(s):
        raise SystemExit("[step341] libraryPage/aboutPage boundary not found")
    s = boundary.sub(METHODS + "    private fun aboutPage()", s, count=1)
    ui.write_text(s, encoding="utf-8")
    print("[step341] Download/install manager UI installed from 3.jpeg reference")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
