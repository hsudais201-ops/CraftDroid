#!/usr/bin/env python3
"""Step 343: add one-click Modrinth downloads, dependency display, and Worlds UI."""
from pathlib import Path
import re
import sys

MARKER = "// STEP343_ONE_CLICK_DOWNLOAD_REQUIRED_WORLD"

METHODS = r'''    // STEP343_ONE_CLICK_DOWNLOAD_REQUIRED_WORLD
    private fun contentSlug(page: String, name: String): String? = when (page to name) {
        "Mod" to "Sodium" -> "sodium"
        "Mod" to "Lithium" -> "lithium"
        "Mod" to "Fabric API" -> "fabric-api"
        "Mod" to "Iris Shaders" -> "iris"
        "Mod" to "JourneyMap" -> "journeymap"
        "Mod" to "OptiFine" -> null
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

    private fun contentLoaderFor(page: String): String {
        return if (page == "Mod") selectedLoader.lowercase(java.util.Locale.ROOT) else "minecraft"
    }

    private fun downloadContent(page: String, name: String) {
        val slug = contentSlug(page, name)
        if (slug == null) {
            if (page == "Mod" && name == "OptiFine") {
                openExternalDownload("https://optifine.net/downloads", "OptiFine downloads")
            } else {
                android.widget.Toast.makeText(this, "$name has no direct download mapping yet", android.widget.Toast.LENGTH_SHORT).show()
            }
            return
        }
        android.widget.Toast.makeText(this, "Finding $name for Minecraft $selectedMinecraftVersion…", android.widget.Toast.LENGTH_SHORT).show()
        Thread {
            try {
                val game = java.net.URLEncoder.encode("[\"$selectedMinecraftVersion\"]", "UTF-8")
                val loader = java.net.URLEncoder.encode("[\"${contentLoaderFor(page)}\"]", "UTF-8")
                val url = java.net.URL("https://api.modrinth.com/v2/project/$slug/version?game_versions=$game&loaders=$loader&featured=true")
                val connection = (url.openConnection() as java.net.HttpURLConnection).apply {
                    requestMethod = "GET"
                    connectTimeout = 10000
                    readTimeout = 15000
                    setRequestProperty("User-Agent", "DroidLauncher/1.0")
                }
                val code = connection.responseCode
                if (code !in 200..299) throw java.io.IOException("HTTP $code")
                val body = connection.inputStream.bufferedReader().use { it.readText() }
                val versions = org.json.JSONArray(body)
                if (versions.length() == 0) throw java.io.IOException("No compatible release found")
                val version = versions.getJSONObject(0)
                val files = version.getJSONArray("files")
                var file: org.json.JSONObject? = null
                for (i in 0 until files.length()) {
                    val candidate = files.getJSONObject(i)
                    if (candidate.optBoolean("primary", false)) { file = candidate; break }
                    if (file == null) file = candidate
                }
                val selectedFile = file ?: throw java.io.IOException("No downloadable file")
                val fileUrl = selectedFile.getString("url")
                val filename = selectedFile.optString("filename", "$name.download")
                val request = android.app.DownloadManager.Request(android.net.Uri.parse(fileUrl)).apply {
                    setTitle("Droid Launcher · $name")
                    setDescription("Minecraft $selectedMinecraftVersion · $selectedLoader")
                    setNotificationVisibility(android.app.DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
                    setAllowedOverMetered(true)
                    setAllowedOverRoaming(true)
                    setDestinationInExternalFilesDir(this@DroidLauncherUiActivity, android.os.Environment.DIRECTORY_DOWNLOADS, "DroidLauncher/$filename")
                }
                val manager = getSystemService(android.content.Context.DOWNLOAD_SERVICE) as android.app.DownloadManager
                manager.enqueue(request)
                runOnUiThread {
                    android.widget.Toast.makeText(this, "Download started: $filename", android.widget.Toast.LENGTH_LONG).show()
                    if (page == "Modpack") showRequiredModsForProject(slug, name)
                }
            } catch (error: Exception) {
                runOnUiThread {
                    android.widget.Toast.makeText(this, "Could not download $name: ${error.message ?: "no compatible file"}", android.widget.Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun showRequiredModsForProject(slug: String, projectName: String) {
        android.widget.Toast.makeText(this, "Checking required mods for $projectName…", android.widget.Toast.LENGTH_SHORT).show()
        Thread {
            try {
                val game = java.net.URLEncoder.encode("[\"$selectedMinecraftVersion\"]", "UTF-8")
                val loader = java.net.URLEncoder.encode("[\"${contentLoaderFor("Mod") }\"]", "UTF-8")
                val url = java.net.URL("https://api.modrinth.com/v2/project/$slug/version?game_versions=$game&loaders=$loader")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 10000
                connection.readTimeout = 15000
                connection.setRequestProperty("User-Agent", "DroidLauncher/1.0")
                if (connection.responseCode !in 200..299) throw java.io.IOException("HTTP ${connection.responseCode}")
                val versions = org.json.JSONArray(connection.inputStream.bufferedReader().use { it.readText() })
                if (versions.length() == 0) throw java.io.IOException("No compatible version")
                val deps = versions.getJSONObject(0).optJSONArray("dependencies")
                val names = mutableListOf<String>()
                if (deps != null) {
                    for (i in 0 until deps.length()) {
                        val dep = deps.getJSONObject(i)
                        if (dep.optString("dependency_type") == "required") {
                            names.add(dep.optString("file_name").ifBlank { dep.optString("project_id") })
                        }
                    }
                }
                runOnUiThread {
                    val message = if (names.isEmpty()) "No required dependency entries were published for this version." else names.joinToString("\n") { "• $it" }
                    android.app.AlertDialog.Builder(this)
                        .setTitle("Required mods · $projectName")
                        .setMessage(message)
                        .setPositiveButton("OK", null)
                        .setNeutralButton("Download all", null)
                        .show()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    android.app.AlertDialog.Builder(this)
                        .setTitle("Required mods · $projectName")
                        .setMessage("Dependency information is unavailable right now.\n\n${error.message ?: "Network error"}")
                        .setPositiveButton("OK", null)
                        .show()
                }
            }
        }.start()
    }

    private fun openExternalDownload(url: String, label: String) {
        try {
            startActivity(android.content.Intent(android.content.Intent.ACTION_VIEW, android.net.Uri.parse(url)))
        } catch (error: Exception) {
            android.widget.Toast.makeText(this, "Cannot open $label", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private fun worldsPage() {
        title.text = "Worlds"
        pageArea.removeAllViews()
        val importCard = roundedCard(16)
        val importRow = LinearLayout(this).apply {
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(12), dp(8), dp(12), dp(8))
        }
        importRow.addView(label("Worlds", 18f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
        val importButton = button("Import world", true)
        importButton.contentDescription = "Import Minecraft world"
        importButton.setOnClickListener {
            val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(android.content.Intent.CATEGORY_OPENABLE)
                type = "application/zip"
                putExtra(android.content.Intent.EXTRA_ALLOW_MULTIPLE, false)
            }
            startActivityForResult(intent, 3431)
        }
        importRow.addView(importButton, LinearLayout.LayoutParams(dp(145), dp(52)))
        importCard.addView(importRow)
        pageArea.addView(importCard)

        listOf("Download World", "Open World Folder", "Create New World").forEach { name ->
            val card = roundedCard(16)
            val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(12), dp(7), dp(12), dp(7)) }
            row.addView(label(name, 15f, true), LinearLayout.LayoutParams(0, dp(54), 1f))
            val action = button(if (name == "Download World") "Download" else "Open")
            action.setOnClickListener {
                when (name) {
                    "Download World" -> openExternalDownload("https://modrinth.com/discover/world", "Minecraft worlds")
                    "Open World Folder" -> android.widget.Toast.makeText(this, "World folder is managed by the selected Minecraft instance", android.widget.Toast.LENGTH_SHORT).show()
                    "Create New World" -> android.widget.Toast.makeText(this, "World creation will open in Minecraft", android.widget.Toast.LENGTH_SHORT).show()
                }
            }
            row.addView(action, LinearLayout.LayoutParams(dp(120), dp(52)))
            card.addView(row)
            pageArea.addView(card)
        }
    }

'''


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step343] missing generated UI: {ui}")
    s = ui.read_text(encoding="utf-8")
    if MARKER in s:
        print("[step343] one-click download/required/world UI already present")
        return 0
    s = s.replace('"Shader Pack" -> listOf("Complementary", "BSL", "Sildur\'s Vibrant", "MakeUp - Ultra Fast")', '"Shader Pack" -> listOf("Complementary", "BSL", "Sildur\'s Vibrant", "MakeUp - Ultra Fast")\n            "World" -> listOf("Download World" to "Minecraft worlds", "Import World" to "Local .zip world", "Create New World" to "In Minecraft")')
    s = s.replace('"Resource Pack" -> "Resource Pack"\n            "Shader Pack" -> "Shader Pack"', '"Resource Pack" -> "Resource Pack"\n            "Shader Pack" -> "Shader Pack"\n            "World" -> "World"')
    s = s.replace('startContentImport(page)', 'downloadContent(page, name)')
    s = s.replace('title.text = "Download - $titleName"', 'title.text = if (page == "World") "Worlds" else "Download - $titleName"')
    boundary = re.compile(r"\n    private fun aboutPage\(\)")
    if not boundary.search(s):
        raise SystemExit("[step343] aboutPage boundary not found")
    s = boundary.sub("\n" + METHODS + "    private fun aboutPage()", s, count=1)
    ui.write_text(s, encoding="utf-8")
    print("[step343] one-click Modrinth downloads, dependency display, and World manager installed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
