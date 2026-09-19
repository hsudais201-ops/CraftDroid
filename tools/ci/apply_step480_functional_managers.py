#!/usr/bin/env python3
"""Step 480: functional content discovery, real server-list ping, version install progress and onboarding."""
from pathlib import Path
import sys

MARKER = "// STEP480_FUNCTIONAL_MANAGERS"

def span(src, sig):
    a = src.find(sig)
    if a < 0:
        raise SystemExit("[step480] missing " + sig)
    brace = src.find("{", a)
    if brace < 0:
        raise SystemExit("[step480] missing brace " + sig)
    depth = 0
    state = "code"
    esc = False
    i = brace
    while i < len(src):
        c = src[i]
        n = src[i + 1] if i + 1 < len(src) else ""
        n2 = src[i + 2] if i + 2 < len(src) else ""
        if state == "line":
            if c == "\n": state = "code"
            i += 1; continue
        if state == "block":
            if c == "*" and n == "/": state = "code"; i += 2
            else: i += 1
            continue
        if state == "triple":
            if c == '"' and n == '"' and n2 == '"': state = "code"; i += 3
            else: i += 1
            continue
        if state == "string":
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': state = "code"
            i += 1; continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = "triple"; i += 3; continue
        if c == '"': state = "string"; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return a, i + 1
        i += 1
    raise SystemExit("[step480] unterminated " + sig)

def replace(src, sig, new):
    a, b = span(src, sig)
    return src[:a] + new + src[b:]

HELPERS = r'''
    // STEP480_FUNCTIONAL_MANAGERS
    private val step480Executor = java.util.concurrent.Executors.newFixedThreadPool(2)

    private fun step480Run(block: () -> Unit) {
        try { step480Executor.execute(block) } catch (_: Throwable) {}
    }

    private fun step480LoadIcon(urlText: String, target: android.widget.ImageView) {
        if (urlText.isBlank()) return
        step480Run {
            try {
                val c = java.net.URL(urlText).openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 5000
                c.readTimeout = 7000
                c.setRequestProperty("User-Agent", "CraftDroid/1.0")
                val o = android.graphics.BitmapFactory.Options().apply {
                    inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
                    inSampleSize = 2
                }
                val bmp = c.inputStream.use { android.graphics.BitmapFactory.decodeStream(it, null, o) }
                c.disconnect()
                if (bmp != null) runOnUiThread { if (!isFinishing) target.setImageBitmap(bmp) }
            } catch (_: Throwable) {}
        }
    }

    private fun step480RemoteCard(type: String, projectId: String, name: String, desc: String, versions: String, iconUrl: String): LinearLayout =
        LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
            setPadding(dp(9), dp(8), dp(9), dp(8))
            background = step479Card("","", "CD") { }.background
            val image = android.widget.ImageView(this@DroidLauncherUiActivity).apply {
                setImageResource(android.R.drawable.ic_menu_gallery)
                scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
            }
            addView(image, LinearLayout.LayoutParams(dp(64), dp(64)))
            val copy = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(9), 0, dp(6), 0)
                addView(step375Text(name.ifBlank { "Unnamed" }, 14f, true))
                addView(step375Text(desc.ifBlank { "No description" }, 10f).apply {
                    maxLines = 2
                    ellipsize = android.text.TextUtils.TruncateAt.END
                    setTextColor(android.graphics.Color.argb(180, 205, 225, 235))
                })
                addView(step375Text("MC versions: " + versions.ifBlank { "unknown" }, 9.5f).apply {
                    setTextColor(android.graphics.Color.rgb(86, 240, 177))
                })
            }
            addView(copy, LinearLayout.LayoutParams(0, dp(72), 1f))
            addView(step375Button("INSTALL", true) {
                step480InstallModrinth(type, projectId)
            }, LinearLayout.LayoutParams(dp(96), dp(44)))
            step480LoadIcon(iconUrl, image)
        }

    private fun step480ManagerPage(type: String) {
        val titleValue = when (type) {
            "Mod" -> "Mods"
            "Modpack" -> "Modpacks"
            "Shader Pack" -> "Shaders"
            "Resource Pack" -> "Resource Packs"
            else -> "Worlds"
        }
        val projectType = when (type) {
            "Mod" -> "mod"
            "Modpack" -> "modpack"
            "Shader Pack" -> "shader"
            "Resource Pack" -> "resourcepack"
            else -> "modpack"
        }
        val queryPrefs = getSharedPreferences("droid_launcher_ui", MODE_PRIVATE)
        val query = queryPrefs.getString("query_" + type, "") ?: ""
        val pageOffset = queryPrefs.getInt("offset_" + type, 0).coerceAtLeast(0)
        pageArea.addView(step375Title(titleValue, "Real Modrinth discovery · search, thumbnails, compatibility and install"))
        val controls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        val field = android.widget.EditText(this).apply {
            hint = "Search " + titleValue.lowercase()
            setSingleLine(true)
            setText(query)
        }
        controls.addView(field, LinearLayout.LayoutParams(0, dp(50), 1f))
        controls.addView(step375Button("SEARCH", true) {
            queryPrefs.edit()
                .putString("query_" + type, field.text.toString())
                .putInt("offset_" + type, 0)
                .apply()
            showPage(type)
        }, LinearLayout.LayoutParams(dp(104), dp(46)).apply { marginStart = dp(7) })
        controls.addView(step375Button("REFRESH") { showPage(type) },
            LinearLayout.LayoutParams(dp(94), dp(46)).apply { marginStart = dp(7) })
        pageArea.addView(controls)

        val listCard = step375Panel(10)
        listCard.addView(step375Text("DISCOVER", 11f, true).apply {
            setTextColor(android.graphics.Color.rgb(86, 240, 177))
        })
        listCard.addView(step375Text("Loading " + titleValue + "…", 12f))
        listCard.addView(android.widget.ProgressBar(this).apply { isIndeterminate = true },
            LinearLayout.LayoutParams(-1, dp(32)))
        pageArea.addView(listCard, LinearLayout.LayoutParams(-1, dp(82)).apply { topMargin = dp(8) })
        if (type == "World") {
            val local = MinecraftContentManager.list(this, MinecraftContentManager.Kind.WORLD)
            if (local.isNotEmpty()) {
                pageArea.addView(step375Text("INSTALLED WORLDS", 11f, true).apply {
                    setTextColor(android.graphics.Color.rgb(86, 240, 177))
                    setPadding(dp(4), dp(10), 0, dp(4))
                })
                local.take(8).forEach { file ->
                    pageArea.addView(step479Row(file.name, "Local world archive", "OPEN", false) {
                        showPage("World")
                    }, LinearLayout.LayoutParams(-1, dp(70)).apply { topMargin = dp(6) })
                }
            }
        }
        step480Run {
            try {
                val q = java.net.URLEncoder.encode(query, "UTF-8")
                val facets = java.net.URLEncoder.encode("[[\"project_type:" + projectType + "\"]]", "UTF-8")
                val u = java.net.URL("https://api.modrinth.com/v2/search?limit=8&offset=" + pageOffset + "&query=" + q + "&facets=" + facets)
                val c = u.openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 7000
                c.readTimeout = 10000
                c.setRequestProperty("User-Agent", "CraftDroid/1.0")
                if (c.responseCode !in 200..299) throw java.io.IOException("Modrinth HTTP " + c.responseCode)
                val json = c.inputStream.bufferedReader().use { it.readText() }
                c.disconnect()
                val hits = org.json.JSONObject(json).optJSONArray("hits") ?: org.json.JSONArray()
                val results = ArrayList<android.os.Bundle>()
                for (i in 0 until hits.length()) {
                    val h = hits.optJSONObject(i) ?: continue
                    val b = android.os.Bundle()
                    b.putString("id", h.optString("project_id"))
                    b.putString("name", h.optString("title"))
                    b.putString("desc", h.optString("description"))
                    b.putString("icon", h.optString("icon_url"))
                    val va = h.optJSONArray("versions")
                    val vv = if (va == null) "" else (0 until minOf(3, va.length())).mapNotNull { va.optString(it).takeIf { it.isNotBlank() } }.joinToString(", ")
                    b.putString("versions", vv)
                    results.add(b)
                }
                runOnUiThread {
                    if (isFinishing || currentPage != type) return@runOnUiThread
                    while (pageArea.childCount > 4) pageArea.removeViewAt(4)
                    if (results.isEmpty() && pageOffset == 0) {
                        val empty = step375Panel(18)
                        empty.gravity = Gravity.CENTER
                        empty.addView(step375Text("No results", 19f, true))
                        empty.addView(step375Text("Try a different search term."))
                        empty.addView(step375Button("RETRY", true) { showPage(type) },
                            LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(8) })
                        pageArea.addView(empty)
                    } else {
                        results.forEach { b ->
                            pageArea.addView(
                                step480RemoteCard(type, b.getString("id"), b.getString("name"), b.getString("desc"), b.getString("versions"), b.getString("icon")),
                                LinearLayout.LayoutParams(-1, dp(104)).apply { topMargin = dp(7) }
                            )
                        }
                        val totalHits = org.json.JSONObject(json).optInt("total_hits", pageOffset + results.size)
                        val nav = LinearLayout(this@DroidLauncherUiActivity).apply {
                            orientation = LinearLayout.HORIZONTAL
                        }
                        if (pageOffset > 0) {
                            nav.addView(step375Button("PREVIOUS") {
                                queryPrefs.edit().putInt("offset_" + type, (pageOffset - 8).coerceAtLeast(0)).apply()
                                showPage(type)
                            }, LinearLayout.LayoutParams(0, dp(46), 1f))
                        }
                        if (pageOffset + results.size < totalHits) {
                            nav.addView(step375Button("NEXT") {
                                queryPrefs.edit().putInt("offset_" + type, pageOffset + results.size).apply()
                                showPage(type)
                            }, LinearLayout.LayoutParams(0, dp(46), 1f).apply {
                                if (pageOffset > 0) marginStart = dp(8)
                            })
                        }
                        if (nav.childCount > 0) {
                            pageArea.addView(nav, LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(8) })
                        }
                        pageArea.addView(step375Text(
                            "Showing real Modrinth results · page " + ((pageOffset / 8) + 1),
                            10f
                        ).apply {
                            setTextColor(android.graphics.Color.argb(155, 200, 220, 230))
                            setPadding(dp(4), dp(8), 0, 0)
                        })
                    }
                }
            } catch (t: Throwable) {
                runOnUiThread {
                    if (isFinishing || currentPage != type) return@runOnUiThread
                    while (pageArea.childCount > 4) pageArea.removeViewAt(4)
                    val error = step375Panel(18)
                    error.addView(step375Text("Library unavailable", 19f, true))
                    error.addView(step375Text(t.message ?: "Network error"))
                    error.addView(step375Button("RETRY", true) { showPage(type) },
                        LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(8) })
                    pageArea.addView(error)
                }
            }
        }
    }

    private fun step480InstallModrinth(type: String, projectId: String) {
        if (!step375HasInstance()) { showPage("Instances"); return }
        val kind = when (type) {
            "Mod" -> MinecraftContentManager.Kind.MOD
            "Modpack" -> MinecraftContentManager.Kind.MODPACK
            "Shader Pack" -> MinecraftContentManager.Kind.SHADER
            "Resource Pack" -> MinecraftContentManager.Kind.RESOURCE_PACK
            else -> MinecraftContentManager.Kind.WORLD
        }
        val dialog = android.app.ProgressDialog(this).apply {
            setTitle("Installing " + type)
            setMessage("Resolving latest compatible file…")
            setProgressStyle(android.app.ProgressDialog.STYLE_HORIZONTAL)
            isIndeterminate = true
            setCancelable(false)
            show()
        }
        step480Run {
            try {
                val vurl = java.net.URL("https://api.modrinth.com/v2/project/" + projectId + "/version")
                val vc = vurl.openConnection() as java.net.HttpURLConnection
                vc.connectTimeout = 7000
                vc.readTimeout = 10000
                vc.setRequestProperty("User-Agent", "CraftDroid/1.0")
                if (vc.responseCode !in 200..299) throw java.io.IOException("Modrinth version HTTP " + vc.responseCode)
                val versions = org.json.JSONArray(vc.inputStream.bufferedReader().use { it.readText() })
                vc.disconnect()
                if (versions.length() == 0) throw java.io.IOException("No published files for this project")
                val v = versions.getJSONObject(0)
                val files = v.optJSONArray("files") ?: throw java.io.IOException("No files")
                var file = files.optJSONObject(0) ?: throw java.io.IOException("No downloadable file")
                for (i in 0 until files.length()) {
                    val candidate = files.optJSONObject(i) ?: continue
                    if (candidate.optBoolean("primary", false)) { file = candidate; break }
                }
                val downloadUrl = file.optString("url")
                val fileName = file.optString("filename", projectId + ".bin")
                if (!downloadUrl.startsWith("https://api.modrinth.com/") && !downloadUrl.startsWith("https://cdn.modrinth.com/")) {
                    throw java.io.IOException("Untrusted content download host")
                }
                val c = java.net.URL(downloadUrl).openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 7000
                c.readTimeout = 15000
                val total = c.contentLengthLong
                runOnUiThread {
                    if (!isFinishing) {
                        dialog.isIndeterminate = total <= 0L
                        dialog.setMessage("Downloading " + fileName)
                        if (total > 0L) dialog.max = 100
                    }
                }
                val tmp = java.io.File(cacheDir, "content-" + System.nanoTime() + ".part")
                c.inputStream.use { input ->
                    java.io.FileOutputStream(tmp).use { out ->
                        val buffer = ByteArray(64 * 1024)
                        var got = 0L
                        while (true) {
                            val n = input.read(buffer)
                            if (n < 0) break
                            out.write(buffer, 0, n)
                            got += n
                            if (total > 0L) runOnUiThread {
                                if (!isFinishing) dialog.progress = ((got * 100L) / total).toInt().coerceIn(0, 100)
                            }
                        }
                    }
                }
                c.disconnect()
                MinecraftContentManager.importFile(this, kind, tmp, fileName)
                tmp.delete()
                runOnUiThread {
                    dialog.dismiss()
                    showPage(type)
                    android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Installed " + fileName, android.widget.Toast.LENGTH_LONG).show()
                }
            } catch (t: Throwable) {
                runOnUiThread {
                    dialog.dismiss()
                    android.app.AlertDialog.Builder(this@DroidLauncherUiActivity)
                        .setTitle("Install failed")
                        .setMessage(t.message ?: "Unknown error")
                        .setPositiveButton("Retry") { _, _ -> step480InstallModrinth(type, projectId) }
                        .setNegativeButton("Close", null)
                        .show()
                }
            }
        }
    }

    private fun step480WriteVarInt(out: java.io.OutputStream, value: Int) {
        var v = value
        do {
            var b = v and 0x7F
            v = v ushr 7
            if (v != 0) b = b or 0x80
            out.write(b)
        } while (v != 0)
    }

    private fun step480ReadVarInt(input: java.io.InputStream): Int {
        var num = 0
        var shift = 0
        while (shift < 35) {
            val b = input.read()
            if (b < 0) throw java.io.EOFException("Server closed connection")
            num = num or ((b and 0x7F) shl shift)
            if ((b and 0x80) == 0) return num
            shift += 7
        }
        throw java.io.IOException("Invalid VarInt")
    }

    private fun step480WriteString(out: java.io.OutputStream, value: String) {
        val bytes = value.toByteArray(Charsets.UTF_8)
        step480WriteVarInt(out, bytes.size)
        out.write(bytes)
    }

    private fun step480ReadString(input: java.io.InputStream): String {
        val size = step480ReadVarInt(input).coerceIn(0, 4 * 1024 * 1024)
        val bytes = ByteArray(size)
        var read = 0
        while (read < size) {
            val n = input.read(bytes, read, size - read)
            if (n < 0) throw java.io.EOFException("Incomplete server response")
            read += n
        }
        return String(bytes, Charsets.UTF_8)
    }

    private fun step480PingServer(host: String, port: Int) {
        step480Run {
            val start = System.currentTimeMillis()
            val result = try {
                java.net.Socket().use { socket ->
                    socket.soTimeout = 4500
                    socket.connect(java.net.InetSocketAddress(host, port), 3500)
                    val out = socket.getOutputStream()
                    val input = socket.getInputStream()
                    val payload = java.io.ByteArrayOutputStream()
                    step480WriteVarInt(payload, 0)
                    step480WriteVarInt(payload, 769)
                    step480WriteString(payload, host)
                    payload.write((port ushr 8) and 0xFF)
                    payload.write(port and 0xFF)
                    step480WriteVarInt(payload, 1)
                    val handshake = payload.toByteArray()
                    val packet = java.io.ByteArrayOutputStream()
                    step480WriteVarInt(packet, handshake.size)
                    packet.write(handshake)
                    out.write(packet.toByteArray())
                    val status = byteArrayOf(0)
                    val req = java.io.ByteArrayOutputStream()
                    step480WriteVarInt(req, status.size)
                    req.write(status)
                    out.write(req.toByteArray())
                    val packetLen = step480ReadVarInt(input)
                    if (packetLen <= 0 || packetLen > 2 * 1024 * 1024) throw java.io.IOException("Invalid status packet")
                    step480ReadVarInt(input)
                    val json = org.json.JSONObject(step480ReadString(input))
                    val description = json.opt("description")
                    val motd = when (description) {
                        is String -> description
                        is org.json.JSONObject -> description.optString("text", description.toString())
                        else -> description?.toString() ?: "MOTD unavailable"
                    }.replace("\n", " ")
                    val players = json.optJSONObject("players")
                    val online = players?.optInt("online", -1) ?: -1
                    val max = players?.optInt("max", -1) ?: -1
                    "Online · " + (System.currentTimeMillis() - start) + " ms · " +
                        (if (online >= 0 && max >= 0) online.toString() + "/" + max else "players unavailable") +
                        "\n" + motd
                }
            } catch (t: Throwable) {
                "Offline · " + (System.currentTimeMillis() - start) + " ms"
            }
            getSharedPreferences("droid_launcher_servers", MODE_PRIVATE).edit()
                .putString("status_" + host + ":" + port, result.substringBefore("\n"))
                .putString("motd_" + host + ":" + port, result.substringAfter("\n", "MOTD unavailable"))
                .apply()
            runOnUiThread { if (!isFinishing && currentPage == "Servers") showPage("Servers") }
        }
    }

    private fun step480ConnectServer(host: String, port: Int) {
        selectServer(host, port)
        if (!step375HasInstance()) { showPage("Instances"); return }
        if (!MinecraftVersionInstallManager.isInstalled(this, selectedMinecraftVersion())) { showPage("Versions"); return }
        if (selectedAccountIndex() < 0) { showPage("Accounts"); return }
        launchSelectedMinecraft()
    }
'''

def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step480] UI missing")
    s = ui.read_text(encoding="utf-8")
    if MARKER not in s:
        pos = s.find("    override fun onCreate(")
        if pos < 0: raise SystemExit("[step480] onCreate anchor missing")
        s = s[:pos] + HELPERS + "\n" + s[pos:]

    first_run = '''    private fun step479FirstRun() {
        pageArea.addView(step375Title("Welcome to CraftDroid", "Welcome → choose version → install → Home"))
        val p = step375Panel(18)
        p.addView(step460LogoBadge("CD", 62))
        p.addView(step375Text("Your first Minecraft install", 23f, true).apply { setPadding(0, dp(12), 0, dp(5)) })
        p.addView(step375Text("Start with the official Minecraft version selector. The install screen shows real progress, cancellation and retry.", 12f))
        p.addView(step375Button("CHOOSE VERSION & INSTALL", true) { showPage("Versions") },
            LinearLayout.LayoutParams(-1, dp(56)).apply { topMargin = dp(14) })
        pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(300)))
    }'''
    s = replace(s, "    private fun step479FirstRun()", first_run)

    versions = '''    private fun step479Versions() {
        pageArea.addView(step375Title("Minecraft Versions", "Official Mojang manifest · persistent install state"))
        val actions = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        actions.addView(step375Button("REFRESH LATEST") { refreshLatestMinecraftVersion(); showPage("Versions") },
            LinearLayout.LayoutParams(0, dp(46), 1f))
        actions.addView(step375Button("JAVA RUNTIME") { showPage("Java") },
            LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginStart = dp(8) })
        pageArea.addView(actions, LinearLayout.LayoutParams(-1, dp(46)))
        pageArea.addView(step375Text("INSTALL LOCATION · launcher Minecraft root", 11f, true).apply {
            setTextColor(android.graphics.Color.rgb(86, 240, 177))
            setPadding(dp(4), dp(9), 0, 0)
        })
        val latest = MinecraftLatestVersionManager.getCached(this)
        if (!latest.isNullOrBlank()) pageArea.addView(step375Text("LATEST · " + latest, 11f, true).apply {
            setTextColor(android.graphics.Color.rgb(86, 240, 177))
            setPadding(dp(4), dp(9), 0, 0)
        })
        minecraftVersionChoices().forEach { version ->
            val state = MinecraftVersionInstallManager.state(this, version)
            val installed = MinecraftVersionInstallManager.isInstalled(this, version)
            val detail = when (state) {
                MinecraftVersionInstallManager.State.INSTALLED -> "Installed · Java " + getResolvedJavaForLaunch(version)
                MinecraftVersionInstallManager.State.DOWNLOADING -> "Installing…"
                MinecraftVersionInstallManager.State.FAILED -> "Previous attempt failed · retry"
                else -> "Not installed · Java " + getResolvedJavaForLaunch(version)
            }
            pageArea.addView(
                step479Row(version, detail, if (installed) "SELECT" else "INSTALL", installed) {
                    if (installed) {
                        saveMinecraftVersion(version)
                        step375Prefs().edit().putBoolean("installed", true).apply()
                        showPage("Home")
                    } else {
                        installMinecraftVersion(version)
                    }
                },
                LinearLayout.LayoutParams(-1, dp(76)).apply { topMargin = dp(7) }
            )
        }
    }'''
    s = replace(s, "    private fun step479Versions()", versions)

    manager = '''    private fun step479Manager(type: String) {
        step480ManagerPage(type)
    }'''
    s = replace(s, "    private fun step479Manager(type:String)", manager)

    servers = '''    private fun step479Servers() {
        pageArea.addView(step375Title("Servers", "Live Minecraft Server List Ping · MOTD · ping · player count"))
        val top = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        top.addView(step375Button("ADD SERVER", true) { showServerDialog(-1) },
            LinearLayout.LayoutParams(0, dp(48), 1f))
        top.addView(step375Button("REFRESH ALL") {
            getSavedServers().forEach { step480PingServer(it.first, it.second) }
        }, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(8) })
        pageArea.addView(top)
        val selected = getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("selected_server", "") ?: ""
        val list = getSavedServers()
        if (list.isEmpty()) {
            val p = step375Panel(20)
            p.gravity = Gravity.CENTER
            p.addView(step460MiniBadge("SRV"))
            p.addView(step375Text("No servers saved", 20f, true))
            p.addView(step375Text("Add a host and port. Status checks run in the background."))
            pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(190)).apply { topMargin = dp(8) })
            return
        }
        list.forEachIndexed { index, server ->
            val host = server.first
            val port = server.second
            val status = getServerStatus(host, port)
            val motd = getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)
                .getString("motd_" + host + ":" + port, "MOTD unavailable") ?: "MOTD unavailable"
            val chosen = (host + ":" + port) == selected
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(10), dp(8), dp(10), dp(8))
                background = android.graphics.drawable.GradientDrawable().apply {
                    cornerRadius = dp(16).toFloat()
                    setColor(android.graphics.Color.argb(228, 12, 19, 30))
                    setStroke(dp(1), android.graphics.Color.argb(90, 75, 230, 175))
                }
            }
            row.addView(step460MiniBadge("SRV"), LinearLayout.LayoutParams(dp(54), dp(54)))
            val c = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(8), 0, dp(7), 0)
                addView(step375Text(getServerName(index).ifBlank { host }, 15f, true))
                addView(step375Text(host + ":" + port + " · " + status, 10.5f).apply {
                    setTextColor(android.graphics.Color.argb(180, 205, 225, 235))
                })
                addView(step375Text(motd, 10f).apply {
                    setMaxLines(1)
                    ellipsize = android.text.TextUtils.TruncateAt.END
                })
            }
            row.addView(c, LinearLayout.LayoutParams(0, dp(72), 1f))
            val buttons = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            buttons.addView(step375Button(if (chosen) "PLAY" else "JOIN", chosen) {
                step480ConnectServer(host, port)
            }, LinearLayout.LayoutParams(dp(84), dp(38)))
            buttons.addView(step375Button("EDIT") { showServerDialog(index) },
                LinearLayout.LayoutParams(dp(84), dp(38)).apply { topMargin = dp(4) })
            row.addView(buttons)
            pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(92)).apply { topMargin = dp(7) })
        }
    }'''
    s = replace(s, "    private fun step479Servers()", servers)

    installer = r'''    private fun installMinecraftVersion(version: String) {
        val content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), 0, dp(20), 0)
        }
        val message = step375Text("Preparing installer…", 11f)
        val bar = android.widget.ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal)
        bar.max = 100
        content.addView(message)
        content.addView(bar, LinearLayout.LayoutParams(-1, dp(30)))
        val dialog = android.app.AlertDialog.Builder(this)
            .setTitle("Install Minecraft " + version)
            .setView(content)
            .setNegativeButton("CANCEL") { _, _ ->
                MinecraftVersionInstallManager.cancel(this@DroidLauncherUiActivity, version)
            }
            .setCancelable(false)
            .create()
        dialog.show()
        MinecraftVersionInstallManager.install(this, version, object : MinecraftVersionInstallManager.Listener {
            override fun onProgress(progress: MinecraftVersionInstallManager.Progress) {
                runOnUiThread {
                    val pct = if (progress.total > 0L) ((progress.downloaded * 100L) / progress.total).toInt().coerceIn(0, 100) else 0
                    bar.progress = pct
                    message.text = progress.stage + " · " + pct + "%"
                }
            }
            override fun onComplete(version: String) {
                saveMinecraftVersion(version)
                step375Prefs().edit().putBoolean("installed", true).apply()
                runOnUiThread {
                    dialog.dismiss()
                    android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Minecraft " + version + " installed", android.widget.Toast.LENGTH_LONG).show()
                    showPage("Home")
                }
            }
            override fun onError(version: String, error: Throwable) {
                runOnUiThread {
                    dialog.dismiss()
                    android.app.AlertDialog.Builder(this@DroidLauncherUiActivity)
                        .setTitle("Install failed")
                        .setMessage(error.message ?: "Unknown error")
                        .setPositiveButton("RETRY") { _, _ -> installMinecraftVersion(version) }
                        .setNegativeButton("CLOSE", null)
                        .show()
                }
            }
        })
    }'''
    s = replace(s, "    private fun installMinecraftVersion(version: String)", installer)

    # Replace the server reachability implementation with actual protocol status ping.
    s = replace(s, "private fun refreshServerStatus(host: String, port: Int)", '''private fun refreshServerStatus(host: String, port: Int) {
        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE).edit()
            .putString("status_" + host + ":" + port, "Checking…")
            .apply()
        step480PingServer(host, port)
    }''')

    s = s.replace("private var step480InstallDialog", "private var step480InstallDialog", 1)

    # Make Home navigation truthful after a fresh state even if an old preference survives.
    old_oncreate = '''        if(step375Prefs().getBoolean("installed",false)) showPage("Home") else showPage("FirstRun")'''
    if old_oncreate in s:
        s = s.replace(old_oncreate, '''        val onboardingComplete = step375Prefs().getBoolean("installed", false)
        if (!onboardingComplete) {
            showPage("FirstRun")
        } else if (minecraftVersionChoices().any { MinecraftVersionInstallManager.isInstalled(this, it) }) {
            showPage("Home")
        } else {
            showPage("Versions")
        }''', 1)

    ui.write_text(s, encoding="utf-8")
    print("[step480] functional content discovery, server ping, version install progress and first-run install flow applied")

if __name__ == "__main__":
    main()
