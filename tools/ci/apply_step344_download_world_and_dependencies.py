#!/usr/bin/env python3
from pathlib import Path
import re
import sys

MARKER = "// STEP344_DOWNLOAD_WORLD_AND_DEPENDENCIES"
METHODS = r'''    // STEP344_DOWNLOAD_WORLD_AND_DEPENDENCIES
    private fun contentSlug(page: String, name: String): String? = when (page to name) {
        "Mod" to "Sodium" -> "sodium"
        "Mod" to "Lithium" -> "lithium"
        "Mod" to "Fabric API" -> "fabric-api"
        "Mod" to "Iris Shaders" -> "iris"
        "Mod" to "JourneyMap" -> "journeymap"
        "Modpack" to "SkyFactory" -> "skyfactory-4"
        "Modpack" to "All the Mods" -> "all-the-mods-10"
        "Modpack" to "Better Minecraft" -> "better-mc-fabric-bmc5"
        "Modpack" to "Create: Perfect World" -> "create-perfect-world"
        "Resource Pack" to "Faithful" -> "faithful-32x"
        "Resource Pack" to "Bare Bones" -> "bare-bones"
        "Resource Pack" to "Stay True" -> "stay-true"
        "Resource Pack" to "Vanilla Tweaks" -> "vanilla-tweaks"
        "Shader Pack" to "Complementary" -> "complementary-reimagined"
        "Shader Pack" to "BSL" -> "bsl-shaders"
        "Shader Pack" to "Sildur's Vibrant" -> "sildurs-vibrant-shaders"
        "Shader Pack" to "MakeUp - Ultra Fast" -> "makeup-ultra-fast-shaders"
        else -> null
    }

    private fun downloadContent(page: String, name: String) {
        val slug = contentSlug(page, name)
        if (slug == null) {
            if (page == "Mod" && name == "OptiFine") {
                try { startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://optifine.net/downloads"))) }
                catch (_: Exception) { android.widget.Toast.makeText(this, "Cannot open OptiFine downloads", android.widget.Toast.LENGTH_SHORT).show() }
            } else android.widget.Toast.makeText(this, "$name has no direct download mapping", android.widget.Toast.LENGTH_SHORT).show()
            return
        }
        Thread {
            try {
                val game = java.net.URLEncoder.encode("[\"$selectedMinecraftVersion\"]", "UTF-8")
                val loaderName = if (page == "Mod") selectedLoader.lowercase(java.util.Locale.ROOT) else "minecraft"
                val loader = java.net.URLEncoder.encode("[\"$loaderName\"]", "UTF-8")
                val api = java.net.URL("https://api.modrinth.com/v2/project/$slug/version?game_versions=$game&loaders=$loader&featured=true")
                val c = api.openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 10000
                c.readTimeout = 15000
                c.setRequestProperty("User-Agent", "DroidLauncher/1.0")
                if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
                val versions = org.json.JSONArray(c.inputStream.bufferedReader().use { it.readText() })
                if (versions.length() == 0) error("No compatible release found")
                val files = versions.getJSONObject(0).getJSONArray("files")
                var file = files.getJSONObject(0)
                for (i in 0 until files.length()) if (files.getJSONObject(i).optBoolean("primary", false)) { file = files.getJSONObject(i); break }
                val url = file.getString("url")
                val filename = file.optString("filename", "$name.download")
                val request = android.app.DownloadManager.Request(android.net.Uri.parse(url)).apply {
                    setTitle("Droid Launcher · $name")
                    setDescription("Minecraft $selectedMinecraftVersion · $selectedLoader")
                    setNotificationVisibility(android.app.DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    setAllowedOverMetered(true)
                    setAllowedOverRoaming(true)
                    setDestinationInExternalFilesDir(this@DroidLauncherUiActivity, android.os.Environment.DIRECTORY_DOWNLOADS, "DroidLauncher/$filename")
                }
                (getSystemService(android.content.Context.DOWNLOAD_SERVICE) as android.app.DownloadManager).enqueue(request)
                runOnUiThread { android.widget.Toast.makeText(this, "Download started: $filename", android.widget.Toast.LENGTH_LONG).show() }
            } catch (e: Exception) {
                runOnUiThread { android.widget.Toast.makeText(this, "Download failed: ${e.message ?: "no compatible file"}", android.widget.Toast.LENGTH_LONG).show() }
            }
        }.start()
    }

    private fun showRequiredModsForProject(slug: String, projectName: String) {
        Thread {
            try {
                val game = java.net.URLEncoder.encode("[\"$selectedMinecraftVersion\"]", "UTF-8")
                val api = java.net.URL("https://api.modrinth.com/v2/project/$slug/version?game_versions=$game")
                val c = api.openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 10000
                c.readTimeout = 15000
                c.setRequestProperty("User-Agent", "DroidLauncher/1.0")
                if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
                val versions = org.json.JSONArray(c.inputStream.bufferedReader().use { it.readText() })
                if (versions.length() == 0) error("No compatible version")
                val deps = versions.getJSONObject(0).optJSONArray("dependencies")
                val names = mutableListOf<String>()
                if (deps != null) for (i in 0 until deps.length()) {
                    val d = deps.getJSONObject(i)
                    if (d.optString("dependency_type") == "required") names.add(d.optString("file_name").ifBlank { d.optString("project_id") })
                }
                runOnUiThread {
                    val text = if (names.isEmpty()) "No required dependency entries published for this version." else names.joinToString("\\n") { "• $it" }
                    android.app.AlertDialog.Builder(this).setTitle("Required mods · $projectName").setMessage(text).setPositiveButton("OK", null).show()
                }
            } catch (e: Exception) {
                runOnUiThread { android.widget.Toast.makeText(this, "Required-mod information unavailable: ${e.message ?: "network error"}", android.widget.Toast.LENGTH_LONG).show() }
            }
        }.start()
    }

    private fun worldsPage() {
        title.text = "Worlds"
        pageArea.removeAllViews()
        val importCard = roundedCard(16)
        val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(8)) }
        row.addView(label("Worlds", 18f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        val importButton = button("Import world", true)
        importButton.contentDescription = "Import Minecraft world"
        importButton.setOnClickListener {
            startActivityForResult(android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(android.content.Intent.CATEGORY_OPENABLE)
                type = "application/zip"
                putExtra(android.content.Intent.EXTRA_ALLOW_MULTIPLE, false)
            }, 3441)
        }
        row.addView(importButton, LinearLayout.LayoutParams(dp(145), dp(52)))
        importCard.addView(row)
        pageArea.addView(importCard)
        val actions = listOf("Download World" to "Download", "Open World Folder" to "Open", "Create New World" to "Open")
        actions.forEach { (name, actionText) ->
            val card = roundedCard(16)
            val r = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12), dp(7), dp(12), dp(7)) }
            r.addView(label(name, 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
            val b = button(actionText)
            b.setOnClickListener {
                if (name == "Download World") {
                    try { startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse("https://modrinth.com/discover/world"))) }
                    catch (_: Exception) { android.widget.Toast.makeText(this, "Cannot open world downloads", android.widget.Toast.LENGTH_SHORT).show() }
                } else android.widget.Toast.makeText(this, "$name is linked to the active Minecraft instance", android.widget.Toast.LENGTH_SHORT).show()
            }
            r.addView(b, LinearLayout.LayoutParams(dp(120), dp(52)))
            card.addView(r)
            pageArea.addView(card)
        }
    }

'''

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit(f"[step344] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s: print("[step344] already applied"); return 0
    if 'startContentImport(page)' not in s: raise SystemExit("[step344] expected content install action not found")
    s = s.replace('startContentImport(page)', 'downloadContent(page, name)')
    anchor = '        pageArea.addView(filterRow)\n'
    world_card = '''        if (page == "Game") {\n            val worldsCard = roundedCard(16)\n            val worldsRow = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12), dp(6), dp(12), dp(6)) }\n            worldsRow.addView(label("Worlds", 15f, true), LinearLayout.LayoutParams(0, dp(48), 1f))\n            val worldsButton = button("Open Worlds", true)\n            worldsButton.contentDescription = "Open Worlds manager"\n            worldsButton.setOnClickListener { worldsPage() }\n            worldsRow.addView(worldsButton, LinearLayout.LayoutParams(dp(140), dp(48)))\n            worldsCard.addView(worldsRow)\n            pageArea.addView(worldsCard)\n        }\n'''
    if anchor not in s: raise SystemExit("[step344] filter row anchor not found")
    s = s.replace(anchor, anchor + world_card, 1)
    boundary = re.compile(r"\n    private fun aboutPage\(\)")
    if not boundary.search(s): raise SystemExit("[step344] aboutPage boundary not found")
    s = boundary.sub("\n" + METHODS + "    private fun aboutPage()", s, count=1)
    ui.write_text(s, encoding="utf-8")
    print("[step344] one-click downloads, required-mod metadata, and Worlds manager installed")
    return 0

if __name__ == "__main__": raise SystemExit(main())
