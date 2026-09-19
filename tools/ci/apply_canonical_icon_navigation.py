#!/usr/bin/env python3
"""Apply the canonical CraftDroid icon/navigation contract after all late UI generation."""
from pathlib import Path
import sys

UI_NAME = "DroidLauncherUiActivity.kt"
MARKER = "// CANONICAL_ICON_NAVIGATION"

def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob(UI_NAME))
    if len(hits) != 1:
        raise SystemExit(f"[canonical-nav] expected one {UI_NAME}, found {len(hits)}")
    return hits[0]

def method_span(source: str, signature: str) -> tuple[int, int]:
    start = source.find(signature)
    if start < 0:
        raise SystemExit(f"[canonical-nav] missing method: {signature}")
    brace = source.find("{", start)
    if brace < 0:
        raise SystemExit(f"[canonical-nav] missing opening brace: {signature}")
    depth = 0
    state = "code"
    escaped = False
    i = brace
    while i < len(source):
        c = source[i]
        n = source[i + 1] if i + 1 < len(source) else ""
        n2 = source[i + 2] if i + 2 < len(source) else ""
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
            if escaped: escaped = False
            elif c == "\\": escaped = True
            elif c == '"': state = "code"
            i += 1; continue
        if c == "/" and n == "/": state = "line"; i += 2; continue
        if c == "/" and n == "*": state = "block"; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': state = "triple"; i += 3; continue
        if c == '"': state = "string"; i += 1; continue
        if c == "{": depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0: return start, i + 1
        i += 1
    raise SystemExit(f"[canonical-nav] unterminated method: {signature}")

def replace_method(source: str, signature: str, replacement: str) -> str:
    a, b = method_span(source, signature)
    return source[:a] + replacement + source[b:]

HELPERS = r'''
    // CANONICAL_ICON_NAVIGATION
    private val canonicalPageHistory = java.util.ArrayDeque<String>()
    private var canonicalBackNavigation = false

    private fun canonicalNavigateBack() {
        if (canonicalPageHistory.isEmpty()) {
            if (currentPage != "Home" && step375Prefs().getBoolean("installed", false)) showPage("Home")
            return
        }
        val target = canonicalPageHistory.removeLast()
        canonicalBackNavigation = true
        try { showPage(target) } finally { canonicalBackNavigation = false }
    }

    private fun canonicalNavigateHome() {
        canonicalPageHistory.clear()
        showPage("Home")
    }

    private fun canonicalSecureMode(): Boolean =
        getSharedPreferences("droid_launcher_security", MODE_PRIVATE).getBoolean("secure_mode", false)

    private fun canonicalToggleSecureMode() {
        val next = !canonicalSecureMode()
        getSharedPreferences("droid_launcher_security", MODE_PRIVATE)
            .edit().putBoolean("secure_mode", next).apply()
        android.widget.Toast.makeText(
            this,
            if (next) "Secure mode enabled" else "Secure mode disabled",
            android.widget.Toast.LENGTH_SHORT
        ).show()
    }

    private fun canonicalOpenTree() {
        try {
            val intent = android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT_TREE)
                .addFlags(
                    android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION or
                        android.content.Intent.FLAG_GRANT_WRITE_URI_PERMISSION or
                        android.content.Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION
                )
            startActivityForResult(intent, 7021)
        } catch (_: Throwable) {
            android.widget.Toast.makeText(this, "Folder picker is unavailable on this device", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private fun canonicalOpenCurrentInstanceFolder() {
        if (!step375HasInstance()) {
            showPage("Instances")
            return
        }
        canonicalOpenTree()
    }

    private fun canonicalOpenServerFolder() {
        canonicalOpenTree()
    }

    private fun canonicalExportInstanceConfig() {
        val instance = if (step375HasInstance()) step375SelectedInstance() else "Minecraft instance"
        val payload = buildString {
            appendLine("CraftDroid instance export")
            appendLine("Instance: $instance")
            appendLine("Minecraft: ${selectedMinecraftVersion()}")
            appendLine("Loader: ${getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE).getString("selected_loader", "Vanilla")}")
        }
        try {
            val send = android.content.Intent(android.content.Intent.ACTION_SEND)
                .setType("text/plain")
                .putExtra(android.content.Intent.EXTRA_SUBJECT, "CraftDroid · $instance")
                .putExtra(android.content.Intent.EXTRA_TEXT, payload)
            startActivity(android.content.Intent.createChooser(send, "Export instance config"))
        } catch (_: Throwable) {
            android.widget.Toast.makeText(this, "Export is unavailable on this device", android.widget.Toast.LENGTH_SHORT).show()
        }
    }

    private fun canonicalSelectLoader(loader: String) {
        getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE)
            .edit().putString("selected_loader", loader).apply()
        showPage("Content")
    }

    private fun canonicalShowVersionFilter() {
        val versions = listOf("Any version", "26.3", "26.2", "26.1.2", "26.1.1", "1.21.11", "1.21.10", "1.21.9", "1.20.6")
        android.app.AlertDialog.Builder(this)
            .setTitle("Minecraft version")
            .setSingleChoiceItems(versions.toTypedArray(), 0) { dialog, which ->
                getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE)
                    .edit().putString("browse_version", versions[which]).apply()
                dialog.dismiss()
                showPage("Content")
            }
            .show()
    }

    private fun canonicalServerPage() {
        pageArea.addView(step375Title("Servers", "Saved Minecraft server connections"))
        val toolbar = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        toolbar.addView(step375Button("+  ADD SERVER", true) { showServerDialog(-1) }, LinearLayout.LayoutParams(0, dp(48), 1f))
        toolbar.addView(step375Button("↻  REFRESH") {
            getSavedServers().forEach { refreshServerStatus(it.first, it.second) }
            showPage("Servers")
        }, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(8) })
        pageArea.addView(toolbar, LinearLayout.LayoutParams(-1, dp(52)))
        val list = getSavedServers()
        if (list.isEmpty()) {
            val empty = step375Panel(20).apply { gravity = Gravity.CENTER }
            empty.addView(step460MiniBadge("SRV"))
            empty.addView(step375Text("No servers saved", 19f, true))
            empty.addView(step375Text("Add a server to monitor ping and manage its local data."))
            pageArea.addView(empty, LinearLayout.LayoutParams(-1, dp(190)).apply { topMargin = dp(8) })
            return
        }
        list.forEachIndexed { index, server ->
            val host = server.first
            val port = server.second
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(9), dp(7), dp(7), dp(7))
                background = step460Surface(48)
            }
            val icon = step460MiniBadge("MC").apply {
                contentDescription = "Server icon"
            }
            row.addView(icon, LinearLayout.LayoutParams(dp(44), dp(44)).apply { marginEnd = dp(8) })
            val center = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
            val nameField = android.widget.EditText(this).apply {
                setSingleLine(true)
                setText(getServerName(index).ifBlank { host })
                hint = "Server name"
                textSize = 15f
                setTextColor(android.graphics.Color.WHITE)
                setHintTextColor(android.graphics.Color.argb(150, 210, 225, 235))
                setPadding(0, 0, 0, 0)
                contentDescription = "Tap to edit server name or address"
                setOnFocusChangeListener { _, focused -> if (focused) showServerDialog(index) }
            }
            center.addView(nameField, LinearLayout.LayoutParams(0, dp(43), 1f))
            center.addView(step375Text("$host:$port", 10.5f).apply {
                setTextColor(android.graphics.Color.argb(165, 210, 228, 236))
            })
            row.addView(center, LinearLayout.LayoutParams(0, dp(58), 1f))
            val signal = TextView(this).apply {
                val status = getServerStatus(host, port)
                text = if (status.contains("online", true) || status.contains("open", true) || status.contains("reachable", true)) "▂▄▆█" else "▂▄▅▆"
                textSize = 13f
                gravity = Gravity.CENTER
                setTextColor(android.graphics.Color.WHITE)
                contentDescription = "Live ping / connection quality: $status"
            }
            row.addView(signal, LinearLayout.LayoutParams(dp(62), dp(48)))
            row.addView(step375Button("▱") {
                selectServer(host, port)
                canonicalOpenServerFolder()
            }, LinearLayout.LayoutParams(dp(48), dp(44)))
            row.addView(step375Button("🗑") {
                deleteServer(index)
                showPage("Servers")
            }, LinearLayout.LayoutParams(dp(48), dp(44)))
            row.setOnClickListener {
                selectServer(host, port)
                showPage("Home")
            }
            pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(70)).apply { topMargin = dp(7) })
        }
    }
'''

def add_helpers(source: str) -> str:
    if MARKER in source:
        return source
    anchor = "    private var currentPage ="
    pos = source.find(anchor)
    if pos < 0:
        raise SystemExit("[canonical-nav] currentPage anchor missing")
    return source[:pos] + HELPERS + "\n" + source[pos:]

def patch_build_ui(source: str) -> str:
    start, end = method_span(source, "    private fun buildUi()")
    block = source[start:end]

    old_step375 = '''        nav.addView(TextView(this).apply { text = "DROID LAUNCHER"; textSize = 20f; setTextColor(android.graphics.Color.WHITE); typeface = Typeface.DEFAULT_BOLD; letterSpacing = .07f }, LinearLayout.LayoutParams(0, dp(54), 1f))
        listOf("▣" to "Instances", "♟" to "Accounts", "⇩" to "Downloads", "⚙" to "Settings").forEach { (i, page) ->
            nav.addView(step375Nav(i) { showPage(page) })
        }'''
    new_step375 = '''        nav.addView(step375Nav("←") { canonicalNavigateBack() })
        nav.addView(TextView(this).apply {
            text = "CRAFTDROID"
            textSize = 20f
            setTextColor(android.graphics.Color.WHITE)
            typeface = Typeface.DEFAULT_BOLD
            letterSpacing = .07f
        }, LinearLayout.LayoutParams(0, dp(54), 1f))
        listOf(
            "⌂" to { canonicalNavigateHome() },
            "▰" to { canonicalOpenCurrentInstanceFolder() },
            "♟" to { showPage("Accounts") },
            "⇩" to { showPage("Content") },
            "⚙" to { showPage("Settings") }
        ).forEach { (i, action) -> nav.addView(step375Nav(i, action)) }'''

    if old_step375 in block:
        block = block.replace(old_step375, new_step375, 1)
        return source[:start] + block + source[end:]

    old_step482 = '''        val destinations = listOf(
            "⌂  Home" to "Home",
            "▣  Instances" to "Instances",
            "◈  Content" to "Content",
            "◉  Servers" to "Servers",
            "♟  Accounts" to "Accounts",
            "J  Java" to "Java",
            "⚙  Settings" to "Settings"
        )
        destinations.forEach { pair ->
            rail.addView(step482NavItem(pair.first) { showPage(pair.second) },
                LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(6) })
        }'''
    new_step482 = '''        val destinations = listOf<kotlin.Pair<String, () -> Unit>>(
            "←  Back" to { canonicalNavigateBack() },
            "⌂  Home" to { canonicalNavigateHome() },
            "▰  Files" to { canonicalOpenCurrentInstanceFolder() },
            "♟  Accounts" to { showPage("Accounts") },
            "⇩  Browse" to { showPage("Content") },
            "◈  Instances" to { showPage("Instances") },
            "◉  Servers" to { showPage("Servers") },
            "J  Java" to { showPage("Java") },
            "⚙  Settings" to { showPage("Settings") }
        )
        destinations.forEach { pair ->
            rail.addView(step482NavItem(pair.first) { pair.second.invoke() },
                LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(6) })
        }'''
    if old_step482 in block:
        block = block.replace(old_step482, new_step482, 1)
        return source[:start] + block + source[end:]

    old_step286 = '''        val home = button("⌂")
        home.setOnClickListener { showPage("Game") }
        val accounts = button("♟")
        accounts.setOnClickListener { showPage("Accounts") }
        val downloads = button("⇩")
        downloads.setOnClickListener { showPage("Search by ID") }
        val settings = button("⚙")
        settings.setOnClickListener { showPage("Renderer") }
        listOf(home, accounts, downloads, settings).forEach {
            top.addView(it, LinearLayout.LayoutParams(dp(52), dp(52)))
        }'''
    new_step286 = '''        val back = button("←")
        back.setOnClickListener { canonicalNavigateBack() }
        val home = button("⌂")
        home.setOnClickListener { canonicalNavigateHome() }
        val files = button("▰")
        files.setOnClickListener { canonicalOpenCurrentInstanceFolder() }
        val accounts = button("♟")
        accounts.setOnClickListener { showPage("Accounts") }
        val downloads = button("⇩")
        downloads.setOnClickListener { showPage("Content") }
        val settings = button("⚙")
        settings.setOnClickListener { showPage("Renderer") }
        listOf(back, home, files, accounts, downloads, settings).forEach {
            top.addView(it, LinearLayout.LayoutParams(dp(52), dp(52)))
        }'''
    if old_step286 in block:
        block = block.replace(old_step286, new_step286, 1)
        return source[:start] + block + source[end:]

    raise SystemExit("[canonical-nav] no supported buildUi navigation layout found")

def patch_show_page(source: str) -> str:
    start, end = method_span(source, "    private fun showPage(page: String)")
    block = source[start:end]

    if "canonicalPageHistory" not in block:
        marker = "pageArea.removeAllViews()"
        pos = block.find(marker)
        if pos < 0:
            raise SystemExit("[canonical-nav] showPage state anchor missing")
        history = '''        if (page == "Home" || page == "Game") {
            canonicalPageHistory.clear()
        } else if (!canonicalBackNavigation && page != currentPage && page != "FirstRun") {
            canonicalPageHistory.addLast(currentPage)
        }
'''
        line_start = block.rfind("\n", 0, pos) + 1
        block = block[:line_start] + history + block[line_start:]

    block = block.replace('"Content","Downloads"->step479Content()', '"Content","Downloads"->canonicalBrowsePage()')
    block = block.replace('"Content", "Downloads" -> step479Content()', '"Content", "Downloads" -> canonicalBrowsePage()')
    block = block.replace('"Content" -> step375Content()', '"Content" -> canonicalBrowsePage()')
    block = block.replace('"Versions"->step479Versions()', '"Versions"->canonicalVersionPage()')

    if '"Content"->canonicalBrowsePage()' not in block and '"Content" -> canonicalBrowsePage()' not in block and '"Content","Downloads"->canonicalBrowsePage()' not in block:
        if 'else->aboutPage()' in block:
            block = block.replace('else->aboutPage()', '"Content"->canonicalBrowsePage()\n            "Downloads"->canonicalBrowsePage()\n            "Versions"->canonicalVersionPage()\n            else->aboutPage()', 1)
        elif 'else -> aboutPage()' in block:
            block = block.replace('else -> aboutPage()', '"Content" -> canonicalBrowsePage()\n            "Downloads" -> canonicalBrowsePage()\n            "Versions" -> canonicalVersionPage()\n            else -> aboutPage()', 1)
    elif '"Versions"->canonicalVersionPage()' not in block and '"Versions" -> canonicalVersionPage()' not in block:
        if 'else->aboutPage()' in block:
            block = block.replace('else->aboutPage()', '"Versions"->canonicalVersionPage()\n            else->aboutPage()', 1)
        elif 'else -> aboutPage()' in block:
            block = block.replace('else -> aboutPage()', '"Versions" -> canonicalVersionPage()\n            else -> aboutPage()', 1)

    return source[:start] + block + source[end:]

def patch_home(source: str) -> str:
    sig = "    private fun step479Home()" if "private fun step479Home()" in source else "    private fun step375Home()"
    start, end = method_span(source, sig)
    block = source[start:end]
    if "canonicalToggleSecureMode()" in block:
        return source
    anchors = (
        '        pageArea.addView(step375Title("Minecraft Dashboard"',
        '        pageArea.addView(step375Title("Home"',
    )
    pos = -1
    for anchor in anchors:
        pos = block.find(anchor)
        if pos >= 0:
            break
    if pos < 0:
        raise SystemExit("[canonical-nav] Home title anchor missing")
    line_end = block.find("\n", pos)
    insert = '''
        val homeActions = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        homeActions.addView(step375Button(if (canonicalSecureMode()) "🔒" else "🔓") {
            canonicalToggleSecureMode()
        }, LinearLayout.LayoutParams(dp(52), dp(48)))
        homeActions.addView(step375Button("＋  New instance") {
            showPage("Instances")
        }, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(7) })
        homeActions.addView(step375Button("↗  Export") {
            canonicalExportInstanceConfig()
        }, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(7) })
        homeActions.addView(step375Button("＋  Add Account") {
            showPage("Accounts")
        }, LinearLayout.LayoutParams(0, dp(48), 1f).apply { marginStart = dp(7) })
        pageArea.addView(homeActions, LinearLayout.LayoutParams(-1, dp(54)))
        pageArea.addView(step375Button(
            if (step375HasInstance()) "INSTANCE  ·  " + step375SelectedInstance() else "INSTANCE  ·  Select an instance"
        ) { showPage("Instances") }, LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(7) })
'''
    block = block[:line_end] + insert + block[line_end:]
    return source[:start] + block + source[end:]

def patch_servers(source: str) -> str:
    sig = "    private fun step479Servers()"
    if sig not in source:
        return source
    start, end = method_span(source, sig)
    replacement = r'''    private fun step479Servers(){
        pageArea.addView(step375Title("Servers","Saved Minecraft server connections · live ping · local data"))
        val top=LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL}
        top.addView(step375Button("+ ADD SERVER",true){showServerDialog(-1)},LinearLayout.LayoutParams(0,dp(48),1f))
        top.addView(step375Button("↻ REFRESH ALL"){getSavedServers().forEach{refreshServerStatus(it.first,it.second)};showPage("Servers")},LinearLayout.LayoutParams(0,dp(48),1f).apply{marginStart=dp(8)})
        pageArea.addView(top)
        val selected=getSharedPreferences("droid_launcher"," MODE_PRIVATE").getString("selected_server","") ?: ""
        val list=getSavedServers()
        if(list.isEmpty()){
            val p=step375Panel(20);p.gravity=Gravity.CENTER
            p.addView(step460MiniBadge("SRV"))
            p.addView(step375Text("No servers saved",20f,true))
            p.addView(step375Text("Add a server to monitor reachability and manage its local folder."))
            pageArea.addView(p,LinearLayout.LayoutParams(-1,dp(200)).apply{topMargin=dp(8)})
            return
        }
        list.forEachIndexed{index,s->
            val host=s.first; val port=s.second; val chosen="$host:$port"==selected
            val row=LinearLayout(this).apply{
                orientation=LinearLayout.HORIZONTAL; gravity=Gravity.CENTER_VERTICAL
                setPadding(dp(9),dp(7),dp(7),dp(7))
                background=step460Surface(48)
            }
            row.addView(step481ServerIcon(host,port),LinearLayout.LayoutParams(dp(54),dp(54)).apply{marginEnd=dp(8)})
            val center=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL}
            val name=android.widget.EditText(this).apply{
                setSingleLine(true)
                setText(getServerName(index).ifBlank{host})
                hint="Server name"
                textSize=15f
                setTextColor(android.graphics.Color.WHITE)
                setHintTextColor(android.graphics.Color.argb(150,210,225,235))
                setPadding(0,0,0,0)
                contentDescription="Tap to edit server name or address"
                setOnFocusChangeListener { _, focused -> if(focused) showServerDialog(index) }
            }
            center.addView(name,LinearLayout.LayoutParams(0,dp(40),1f))
            center.addView(step375Text("$host:$port  ·  "+getServerStatus(host,port),10.5f).apply{setTextColor(android.graphics.Color.argb(175,205,225,235))})
            row.addView(center,LinearLayout.LayoutParams(0,dp(58),1f))
            val signal=step460MiniBadge("▂▄▆█").apply{contentDescription="Live ping / connection quality"}
            row.addView(signal,LinearLayout.LayoutParams(dp(62),dp(44)).apply{marginStart=dp(5)})
            row.addView(step375Button("▱"){selectServer(host,port);canonicalOpenServerFolder()},LinearLayout.LayoutParams(dp(46),dp(42)).apply{marginStart=dp(5)})
            row.addView(step375Button("🗑"){deleteServer(index);showPage("Servers")},LinearLayout.LayoutParams(dp(46),dp(42)).apply{marginStart=dp(5)})
            pageArea.addView(row,LinearLayout.LayoutParams(-1,dp(72)).apply{topMargin=dp(7)})
        }
    }
'''
    replacement = replacement.replace('" MODE_PRIVATE"', ' MODE_PRIVATE')
    return source[:start] + replacement + source[end:]

def patch_accounts(source: str) -> str:
    replacements = {
        'step375Button("+  MICROSOFT", true)': 'step375Button("＋  Microsoft account", true)',
        'step375Button("+  OFFLINE")': 'step375Button("＋  Offline account")',
        'step375Button("+  OTHER")': 'step375Button("＋  Another way")',
        'step375Button(if (i == selectedAccountIndex()) "SELECTED" else "SELECT")': 'step375Button("▶")',
        'step375Button("EDIT")': 'step375Button("✎")',
        'step375Button("DELETE")': 'step375Button("🗑")',
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source

def patch_account_detail(source: str) -> str:
    start, end = method_span(source, "    private fun step375AccountDetail(microsoft: Boolean)")
    block = source[start:end]
    if 'SIGN IN FROM MICROSOFT' not in block:
        anchor = '        val cos = step375Panel(12);'
        if anchor not in block:
            raise SystemExit("[canonical-nav] cosmetics panel anchor missing")
        block = block.replace(
            anchor,
            '        if (microsoft) info.addView(step375Button("SIGN IN FROM MICROSOFT", true) { showMicrosoftSignInPage() }, LinearLayout.LayoutParams(-1, dp(46)).apply { topMargin = dp(8) })\n' + anchor,
            1,
        )
    return source[:start] + block + source[end:]

def patch_loader_strip(source: str) -> str:
    start, end = method_span(source, "    private fun step460LoaderStrip()")
    replacement = r'''    private fun step460LoaderStrip(): android.widget.HorizontalScrollView =
        android.widget.HorizontalScrollView(this).apply {
            isHorizontalScrollBarEnabled = false
            val row = LinearLayout(this@DroidLauncherUiActivity).apply {
                orientation = LinearLayout.HORIZONTAL
                listOf(
                    "Vanilla", "OptiFine", "Fabric", "Quilt", "Legacy Fabric",
                    "Forge", "NeoForge", "Modpack"
                ).forEach { loader ->
                    addView(
                        step460CategoryCard(
                            if (loader == "OptiFine") "OF" else loader.take(2).uppercase(),
                            loader,
                            "Loader filter",
                            { canonicalSelectLoader(loader) }
                        ),
                        LinearLayout.LayoutParams(dp(164), dp(68)).apply { marginEnd = dp(7) }
                    )
                }
            }
            addView(row)
        }'''
    return source[:start] + replacement + source[end:]

def ensure_extra_helpers(source: str) -> str:
    if "private fun canonicalBrowsePage()" in source:
        return source
    anchor = "    private fun canonicalServerPage()"
    if anchor not in source:
        raise SystemExit("[canonical-nav] helper insertion anchor missing")
    extra = r'''
    private fun canonicalBrowsePage() {
        pageArea.addView(step375Title("Browse", "Live Modrinth content · content type · Minecraft version"))
        val filters = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        val prefs = getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE)
        filters.addView(step375Button("MODRINTH", true) {
            prefs.edit().putString("source", "Modrinth").apply()
            android.widget.Toast.makeText(this, "Modrinth selected", android.widget.Toast.LENGTH_SHORT).show()
        }, LinearLayout.LayoutParams(0, dp(46), 1f))
        filters.addView(step375Button("CURSEFORGE") {
            prefs.edit().putString("source", "CurseForge").apply()
            android.widget.Toast.makeText(this, "CurseForge selected", android.widget.Toast.LENGTH_SHORT).show()
        }, LinearLayout.LayoutParams(0, dp(46), 1f).apply { marginStart = dp(7) })
        filters.addView(step375Button(
            prefs.getString("browse_version", "Any version") ?: "Any version"
        ) { canonicalShowVersionFilter() }, LinearLayout.LayoutParams(dp(150), dp(46)).apply { marginStart = dp(7) })
        pageArea.addView(filters, LinearLayout.LayoutParams(-1, dp(52)))

        val types = listOf(
            "Modpack" to "PACK",
            "Resource Pack" to "RES",
            "Shader Pack" to "FX",
            "Mod" to "MOD",
            "World" to "WRLD"
        )
        types.forEach { pair ->
            pageArea.addView(
                step460CategoryCard(
                    pair.second, pair.first, "Content type",
                    { step391StartContentImport(pair.first) }
                ),
                LinearLayout.LayoutParams(-1, dp(76)).apply { topMargin = dp(7) }
            )
        }
    }

    private fun canonicalVersionPage() {
        pageArea.addView(step375Title("Minecraft Versions", "Vanilla releases · grass-block version entries"))
        val versions = listOf("26.3","26.2","26.1.2","26.1.1","1.21.11","1.21.10","1.21.9","1.20.6","1.20.4")
        versions.forEach { version ->
            val installed = MinecraftVersionInstallManager.isInstalled(this, version)
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER_VERTICAL
                setPadding(dp(9), dp(7), dp(9), dp(7))
                background = step460Surface(48)
            }
            row.addView(
                step460MiniBadge("🌿").apply { contentDescription = "Grass block version tile" },
                LinearLayout.LayoutParams(dp(48), dp(48)).apply { marginEnd = dp(9) }
            )
            row.addView(step375Text(version, 16f, true), LinearLayout.LayoutParams(0, dp(52), 1f))
            row.addView(step375Button(
                if (installed) "SELECT" else "INSTALL", installed
            ) {
                saveMinecraftVersion(version)
                if (installed) showPage("Home") else installMinecraftVersion(version)
            }, LinearLayout.LayoutParams(dp(112), dp(44)))
            pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(68)).apply { topMargin = dp(7) })
        }
    }
'''
    return source.replace(anchor, extra + "\n" + anchor, 1)

def patch_content(source: str) -> str:
    start, end = method_span(source, "    private fun step375Content()")
    block = source[start:end]
    if "Modrinth" not in block:
        anchor = '        pageArea.addView(step375Title("Downloads"'
        pos = block.find(anchor)
        if pos < 0:
            raise SystemExit("[canonical-nav] Downloads title anchor missing")
        line_end = block.find("\n", pos)
        insertion = '''
        val browseFilters = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        browseFilters.addView(step375Button("MODRINTH") {
            getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE).edit().putString("source", "Modrinth").apply()
            showPage("Content")
        }, LinearLayout.LayoutParams(0, dp(44), 1f))
        browseFilters.addView(step375Button("CURSEFORGE") {
            getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE).edit().putString("source", "CurseForge").apply()
            showPage("Content")
        }, LinearLayout.LayoutParams(0, dp(44), 1f).apply { marginStart = dp(7) })
        browseFilters.addView(step375Button(
            getSharedPreferences("droid_launcher_canonical_ui", MODE_PRIVATE).getString("browse_version", "Any version") ?: "Any version"
        ) { canonicalShowVersionFilter() }, LinearLayout.LayoutParams(dp(145), dp(44)).apply { marginStart = dp(7) })
        pageArea.addView(browseFilters, LinearLayout.LayoutParams(-1, dp(50)).apply { bottomMargin = dp(6) })
'''
        block = block[:line_end] + insertion + block[line_end:]
    block = block.replace(
        'row.addView(step460MiniBadge("MC"), LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginEnd = dp(7) })',
        'row.addView(step460MiniBadge("🌿").apply { contentDescription = "Grass block version tile" }, LinearLayout.LayoutParams(dp(40), dp(40)).apply { marginEnd = dp(7) })',
        1,
    )
    return source[:start] + block + source[end:]

def patch_settings(source: str) -> str:
    start, end = method_span(source, "    private fun step375Settings()")
    block = source[start:end]
    if 'step375Button("TOUCH CONTROLS"' not in block:
        anchor = '        pageArea.addView(step375Title("Settings"'
        pos = block.find(anchor)
        if pos < 0:
            raise SystemExit("[canonical-nav] Settings title anchor missing")
        line_end = block.find("\n", pos)
        insertion = '\n        pageArea.addView(step375Button("TOUCH CONTROLS") { showPage("Controls") }, LinearLayout.LayoutParams(-1, dp(48)).apply { bottomMargin = dp(7) })'
        block = block[:line_end] + insertion + block[line_end:]
    return source[:start] + block + source[end:]

def normalize_copy(source: str) -> str:
    replacements = {
        "Obtifine": "OptiFine",
        "dofault": "default",
        "mabile": "mobile",
        "onnce": "once",
        "acconding": "according",
    }
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = find_ui(root)
    source = ui.read_text(encoding="utf-8")
    source = add_helpers(source)
    source = ensure_extra_helpers(source)
    source = patch_build_ui(source)
    source = patch_show_page(source)
    source = patch_home(source)
    source = patch_accounts(source)
    source = patch_account_detail(source)
    source = patch_servers(source)
    source = patch_loader_strip(source)
    source = patch_content(source)
    source = patch_settings(source)
    source = normalize_copy(source)
    ui.write_text(source, encoding="utf-8")

    required = (
        "CANONICAL_ICON_NAVIGATION",
        "canonicalNavigateBack",
        "canonicalNavigateHome",
        "canonicalOpenCurrentInstanceFolder",
        "canonicalExportInstanceConfig",
        "canonicalBrowsePage",
        "canonicalVersionPage",
        "OptiFine",
        "Legacy Fabric",
        "Forge",
        "NeoForge",
        "Modpack",
        "Modrinth",
        "CurseForge",
        "Any version",
        "TOUCH CONTROLS",
        "SIGN IN FROM MICROSOFT",
        "Grass block version tile",
    )
    missing = [x for x in required if x not in source]
    if missing:
        raise SystemExit("[canonical-nav] missing contracts: " + ", ".join(missing))
    print("[canonical-nav] canonical icon/action navigation, loader filters, browse filters and copy fixes applied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
