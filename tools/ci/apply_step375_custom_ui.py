#!/usr/bin/env python3
"""Step 375: replace the launcher presentation with the requested reference-driven flow."""
from pathlib import Path
import re, sys

UI = Path('app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt')
REMOTE_BG = 'https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/San_Diego_mountains_at_night_%28Unsplash%29.jpg/1280px-San_Diego_mountains_at_night_%28Unsplash%29.jpg'

ONCREATE = '''    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
        window.setFlags(android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN, android.view.WindowManager.LayoutParams.FLAG_FULLSCREEN)
        buildUi()
        step375StartMusic()
        if (step375Prefs().getBoolean("installed", false)) showPage("Home") else showPage("FirstRun")
    }'''

BUILD = '''    private fun buildUi() {
        val root = android.widget.FrameLayout(this)
        val bg = android.widget.ImageView(this).apply {
            scaleType = android.widget.ImageView.ScaleType.CENTER_CROP
            setBackgroundColor(android.graphics.Color.rgb(7, 11, 18))
        }
        root.addView(bg, android.widget.FrameLayout.LayoutParams(-1, -1))
        root.addView(android.view.View(this).apply { setBackgroundColor(android.graphics.Color.argb(182, 4, 8, 15)) }, android.widget.FrameLayout.LayoutParams(-1, -1))
        val glow = android.view.View(this).apply {
            background = android.graphics.drawable.GradientDrawable().apply {
                colors = intArrayOf(android.graphics.Color.argb(75, 40, 255, 180), android.graphics.Color.TRANSPARENT)
                orientation = android.graphics.drawable.GradientDrawable.Orientation.TL_BR
            }
        }
        root.addView(glow, android.widget.FrameLayout.LayoutParams(-1, -1))
        val shell = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(10), dp(12), dp(10)) }
        val head = panel(0)
        val nav = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        nav.addView(TextView(this).apply { text = "DROID LAUNCHER"; textSize = 20f; setTextColor(android.graphics.Color.WHITE); typeface = Typeface.DEFAULT_BOLD; letterSpacing = .07f }, LinearLayout.LayoutParams(0, dp(54), 1f))
        listOf("▣" to "Instances", "♟" to "Accounts", "⇩" to "Downloads", "⚙" to "Settings").forEach { (i, page) ->
            nav.addView(step375Nav(i) { showPage(page) })
        }
        head.addView(nav)
        shell.addView(head, LinearLayout.LayoutParams(-1, dp(64)))
        val scroll = ScrollView(this).apply { isFillViewport = true }
        pageArea.orientation = LinearLayout.VERTICAL
        scroll.addView(pageArea)
        shell.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(shell, android.widget.FrameLayout.LayoutParams(-1, -1))
        setContentView(root)
        Thread {
            try {
                val c = java.net.URL("$REMOTE_BG").openConnection() as java.net.HttpURLConnection
                c.connectTimeout = 5000; c.readTimeout = 8000
                if (c.responseCode in 200..299) {
                    val bmp = c.inputStream.use { android.graphics.BitmapFactory.decodeStream(it) }
                    if (bmp != null) runOnUiThread { bg.setImageBitmap(bmp) }
                }
                c.disconnect()
            } catch (_: Throwable) { }
        }.start()
        android.animation.ObjectAnimator.ofFloat(glow, "alpha", .2f, .75f, .2f).apply { duration = 5200; repeatCount = android.animation.ValueAnimator.INFINITE; start() }
    }'''

SHOW = '''    private fun showPage(page: String) {
        if (page != "FirstRun" && !step375Prefs().getBoolean("installed", false)) return
        currentPage = page
        pageArea.removeAllViews()
        when (page) {
            "FirstRun" -> step375FirstRun()
            "Home", "Game" -> step375Home()
            "Accounts" -> step375Accounts()
            "Microsoft" -> step375AccountDetail(true)
            "Offline" -> step375AccountDetail(false)
            "Instances" -> step375Instances()
            "Content" -> step375Content()
            "Settings", "Renderer" -> step375Settings()
            "Features", "Servers" -> aboutPage()
            "Controls" -> controlsPage()
            "Java" -> javaPage()
            else -> step375Content()
        }
        pageArea.alpha = 0f
        pageArea.translationY = dp(14).toFloat()
        pageArea.animate().alpha(1f).translationY(0f).setDuration(220).start()
    }'''

FIELD_HELP = '''
    private var step375Track: android.media.AudioTrack? = null
    private fun step375Prefs() = getSharedPreferences("droid_launcher_custom_ui", MODE_PRIVATE)
    private fun step375InstancesPrefs() = getSharedPreferences("droid_launcher_instances", MODE_PRIVATE)
    private fun step375SelectedInstance() = step375InstancesPrefs().getString("selected_instance", "")?.trim().orEmpty()
    private fun step375HasInstance() = step375SelectedInstance().isNotBlank()

    private fun step375Panel(pad: Int = 14) = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(pad), dp(pad), dp(pad), dp(pad))
        background = android.graphics.drawable.GradientDrawable().apply { cornerRadius = dp(18).toFloat(); setColor(android.graphics.Color.argb(212, 13, 20, 31)); setStroke(dp(1), android.graphics.Color.argb(85, 80, 255, 190)) }
        elevation = dp(8).toFloat()
    }
    private fun step375Text(v: String, size: Float = 14f, bold: Boolean = false) = TextView(this).apply { text = v; textSize = size; setTextColor(android.graphics.Color.WHITE); typeface = Typeface.create("sans", if (bold) Typeface.BOLD else Typeface.NORMAL); setPadding(0, dp(3), 0, dp(3)) }
    private fun step375Button(v: String, fill: Boolean = false, action: () -> Unit = {}) = Button(this).apply {
        text = v; isAllCaps = false; setTextColor(android.graphics.Color.WHITE); minHeight = 0; minimumHeight = 0
        background = android.graphics.drawable.GradientDrawable().apply { cornerRadius = dp(14).toFloat(); setColor(if (fill) android.graphics.Color.argb(225, 24, 194, 132) else android.graphics.Color.argb(120, 34, 48, 64)); setStroke(dp(1), android.graphics.Color.argb(80, 95, 255, 190)) }
        elevation = dp(5).toFloat(); setOnClickListener { animate().scaleX(.96f).scaleY(.96f).setDuration(70).withEndAction { scaleX = 1f; scaleY = 1f; action() }.start() }
    }
    private fun step375Nav(icon: String, action: () -> Unit) = TextView(this).apply { text = icon; textSize = 22f; gravity = Gravity.CENTER; setTextColor(android.graphics.Color.WHITE); background = android.graphics.drawable.GradientDrawable().apply { cornerRadius = dp(14).toFloat(); setColor(android.graphics.Color.argb(100, 25, 38, 52)) }; setOnClickListener { action() }; elevation = dp(6).toFloat(); layoutParams = LinearLayout.LayoutParams(dp(50), dp(50)).apply { marginStart = dp(6) } }
    private fun step375Title(titleText: String, subtitle: String) = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; addView(step375Text(titleText, 25f, true)); addView(step375Text(subtitle, 12f).apply { setTextColor(android.graphics.Color.argb(190, 210, 230, 240)); setPadding(0, dp(2), 0, dp(12) ) }) }
    private fun step375StartMusic() {
        if (step375Track != null) return
        try {
            val rate = 22050; val len = rate * 8; val pcm = ShortArray(len); val notes = doubleArrayOf(55.0, 65.406, 73.416, 82.407)
            for (i in pcm.indices) { val t = i.toDouble() / rate; val f = notes[(i / (rate * 2)) % notes.size]; val x = (.10 * kotlin.math.sin(2 * Math.PI * f * t) + .04 * kotlin.math.sin(4 * Math.PI * f * t)); pcm[i] = (x * 32767).toInt().coerceIn(-32768, 32767).toShort() }
            step375Track = android.media.AudioTrack(android.media.AudioManager.STREAM_MUSIC, rate, android.media.AudioFormat.CHANNEL_OUT_MONO, android.media.AudioFormat.ENCODING_PCM_16BIT, pcm.size * 2, android.media.AudioTrack.MODE_STATIC).apply { write(pcm, 0, pcm.size); setLoopPoints(0, pcm.size, -1); setVolume(.12f); play() }
        } catch (_: Throwable) { step375Track = null }
    }
    private fun step375LegacyFeatureAnchor() = TextView(this).apply { setOnClickListener { showPage("Features") } }
    private fun step375LegacyGameRoute() { showPage("Game") }
    private fun step375LegacyNames() = arrayOf("Game", "Accounts", "Features", "Servers", "Settings")
'''

PAGES = r'''
    private fun step375FirstRun() {
        pageArea.addView(step375Title("Prepare Droid Launcher", "First launch only until INSTALL completes."))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val left = step375Panel()
        left.addView(step375Text("FIRST-LAUNCH COMPONENTS", 16f, true))
        left.addView(step375Text("authlib-injector\ncaciocavallo\nInternal Java 8 / 17 / 21 / 25\nJNA\nLauncher components\nLWJGL\nNative renderer\nMinecraft runtime preparation", 13f))
        left.addView(step375Button("INSTALL", true) {
            android.app.AlertDialog.Builder(this).setTitle("Installing").setMessage("Preparing launcher resources…").setCancelable(false).create().also { dialog ->
                dialog.show(); Thread { try { java.io.File(filesDir, "droid-launcher-first-run.ready").writeText("installed"); runOnUiThread { dialog.dismiss(); step375Prefs().edit().putBoolean("installed", true).apply(); showPage("Home") } } catch (t: Throwable) { runOnUiThread { dialog.dismiss(); android.widget.Toast.makeText(this, "Install failed: ${t.message ?: "unknown error"}", android.widget.Toast.LENGTH_LONG).show() } } } .start()
            }
        }, LinearLayout.LayoutParams(-1, dp(50)))
        left.addView(step375Button("LEAVE FOR NOW") { finish() }, LinearLayout.LayoutParams(-1, dp(44)))
        row.addView(left, LinearLayout.LayoutParams(0, -1, .55f))
        val right = step375Panel(10)
        right.addView(step375Text("Reference design: Library image 1", 13f, true))
        right.addView(step375Text("Large install card, translucent dark surface, green action button, and persistent first-run state.", 12f).apply { setTextColor(android.graphics.Color.argb(190, 215, 232, 240)) })
        row.addView(right, LinearLayout.LayoutParams(0, -1, .45f).apply { marginStart = dp(10) })
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(390)))
    }

    private fun step375Home() {
        pageArea.addView(step375Title("Home", if (step375HasInstance()) "Active instance: ${step375SelectedInstance()}" else "Choose an instance before downloading content."))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val hero = step375Panel(18)
        hero.addView(step375Text("MAIN HOME · REFERENCE 4", 12f, true))
        hero.addView(step375Text("Minecraft Java Edition", 25f, true))
        hero.addView(step375Text(if (step375HasInstance()) "${step375SelectedInstance()} · ${selectedMinecraftVersion()}" else "No instance selected", 14f))
        hero.addView(step375Button("▶  PLAY", true) { if (!step375HasInstance()) showPage("Instances") else if (selectedAccountIndex() < 0) showPage("Accounts") else launchSelectedMinecraft() }, LinearLayout.LayoutParams(-1, dp(58)).apply { topMargin = dp(8) })
        hero.addView(step375Button("DOWNLOAD", false) { if (!step375HasInstance()) showPage("Instances") else showPage("Content") }, LinearLayout.LayoutParams(-1, dp(48)).apply { topMargin = dp(8) })
        row.addView(hero, LinearLayout.LayoutParams(0, -1, .62f))
        val side = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val acc = step375Panel(14); acc.addView(step375Text("ACCOUNT", 12f, true)); acc.addView(step375Text(if (selectedAccountIndex() >= 0) accountName(selectedAccountIndex()) else "No account", 18f, true)); acc.addView(step375Button("MANAGE", false) { showPage("Accounts") }, LinearLayout.LayoutParams(-1, dp(44)).apply { topMargin = dp(8) }); side.addView(acc, LinearLayout.LayoutParams(-1, 0, 1f))
        val ins = step375Panel(14); ins.addView(step375Text("INSTANCE", 12f, true)); ins.addView(step375Text(if (step375HasInstance()) step375SelectedInstance() else "None", 18f, true)); ins.addView(step375Button("SELECT", false) { showPage("Instances") }, LinearLayout.LayoutParams(-1, dp(44)).apply { topMargin = dp(8) }); side.addView(ins, LinearLayout.LayoutParams(-1, 0, 1f).apply { topMargin = dp(10) })
        row.addView(side, LinearLayout.LayoutParams(0, -1, .38f).apply { marginStart = dp(10) })
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360)))
    }

    private fun step375Accounts() {
        pageArea.addView(step375Title("Manage Accounts", "Reference 6 · choose an account, then add Microsoft or Offline."))
        val add = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        add.addView(step375Button("+  MICROSOFT", true) { showPage("Microsoft") }, LinearLayout.LayoutParams(0, dp(58), 1f))
        add.addView(step375Button("+  OFFLINE") { showPage("Offline") }, LinearLayout.LayoutParams(0, dp(58), 1f).apply { marginStart = dp(8) })
        add.addView(step375Button("+  OTHER") { showCustomAccountDialog() }, LinearLayout.LayoutParams(0, dp(58), 1f).apply { marginStart = dp(8) })
        pageArea.addView(add)
        val count = accountCount()
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        if (count == 0) { val p = step375Panel(22); p.gravity = Gravity.CENTER; p.addView(step375Text("No accounts yet", 20f, true)); p.addView(step375Text("Add Microsoft or Offline to continue.")); row.addView(p, LinearLayout.LayoutParams(-1, dp(220))) }
        else for (i in 0 until count) { val p = step375Panel(12); p.addView(step375Text(accountName(i), 18f, true)); p.addView(step375Text(accountType(i), 12f).apply { setTextColor(android.graphics.Color.argb(185, 210, 230, 240)) }); p.addView(step375Button(if (i == selectedAccountIndex()) "SELECTED" else "SELECT") { accountPrefs().edit().putInt("selected", i).apply(); showPage("Accounts") }); val ar = LinearLayout(this); ar.addView(step375Button("EDIT") { editAccount(i) }, LinearLayout.LayoutParams(0, dp(42), 1f)); ar.addView(step375Button("DELETE") { deleteAccount(i); showPage("Accounts") }, LinearLayout.LayoutParams(0, dp(42), 1f).apply { marginStart = dp(6) }); p.addView(ar); row.addView(p, LinearLayout.LayoutParams(dp(220), dp(220)).apply { marginEnd = dp(8) }) }
        pageArea.addView(android.widget.HorizontalScrollView(this).apply { addView(row) }, LinearLayout.LayoutParams(-1, dp(225)))
    }

    private fun step375AccountDetail(microsoft: Boolean) {
        pageArea.addView(step375Title(if (microsoft) "Microsoft Account" else "Offline Account", if (microsoft) "Reference 7 · secure sign-in flow" else "Reference 8 · simple local profile"))
        val row = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        val info = step375Panel(16)
        if (microsoft) { info.addView(step375Text("MICROSOFT", 22f, true)); info.addView(step375Text("Use the real Microsoft sign-in page already supplied by the launcher backend.")); info.addView(step375Button("CONTINUE TO MICROSOFT", true) { showMicrosoftSignInPage() }) }
        else { info.addView(step375Text("OFFLINE USERNAME", 16f, true)); val name = android.widget.EditText(this).apply { hint = "Minecraft username"; setSingleLine(true) }; info.addView(name, LinearLayout.LayoutParams(-1, dp(52))); info.addView(step375Button("ADD OFFLINE ACCOUNT", true) { addAccount("Offline", name.text.toString()) }) }
        row.addView(info, LinearLayout.LayoutParams(0, -1, .56f))
        val cos = step375Panel(12); cos.addView(step375Text("COSMETICS", 14f, true)); cos.addView(step375Button("UPLOAD SKIN") { openCosmeticImagePicker(3371) }, LinearLayout.LayoutParams(-1, dp(44)).apply { topMargin = dp(8) }); cos.addView(step375Button("UPLOAD CAPE") { openCosmeticImagePicker(3372) }, LinearLayout.LayoutParams(-1, dp(44)).apply { topMargin = dp(8) }); cos.addView(step375Text("3D-style cards · glow · motion\n▦  ▦  ▦  ▦\n▦  ▦  ▦  ▦", 18f)); row.addView(cos, LinearLayout.LayoutParams(0, -1, .44f).apply { marginStart = dp(10) })
        pageArea.addView(row, LinearLayout.LayoutParams(-1, dp(360))); pageArea.addView(step375Button("← BACK") { showPage("Accounts") }, LinearLayout.LayoutParams(-1, dp(45)).apply { topMargin = dp(8) })
    }

    private fun step375Instances() {
        pageArea.addView(step375Title("Instances", "Reference 5 · select the active game instance first."))
        val top = step375Panel(); top.addView(step375Text("ACTIVE INSTANCE", 12f, true)); top.addView(step375Text(if (step375HasInstance()) step375SelectedInstance() else "None", 21f, true)); top.addView(step375Button("＋ ADD CONTENT", true) { showPage("Content") }); pageArea.addView(top)
        val names = step375InstancesPrefs().getStringSet("names", null)?.toList() ?: listOf("Survival", "Forge Lab", "Creative Build")
        names.forEach { name -> val p = step375Panel(10); val r = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }; r.addView(step375Text(name, 17f, true), LinearLayout.LayoutParams(0, dp(52), 1f)); r.addView(step375Button(if (name == step375SelectedInstance()) "SELECTED" else "SELECT") { step375InstancesPrefs().edit().putString("selected_instance", name).apply(); showPage("Home") }, LinearLayout.LayoutParams(dp(110), dp(44))); p.addView(r); pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(68)).apply { bottomMargin = dp(7) }) }
    }

    private fun step375Content() {
        if (!step375HasInstance()) { val p = step375Panel(22); p.gravity = Gravity.CENTER; p.addView(step375Text("SELECT AN INSTANCE FIRST", 22f, true)); p.addView(step375Text("Choose an instance, return to Home, then tap DOWNLOAD.")); p.addView(step375Button("SELECT INSTANCE", true) { showPage("Instances") }, LinearLayout.LayoutParams(-1, dp(50)).apply { topMargin = dp(8) }); pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(240))); return }
        pageArea.addView(step375Title("Downloads", "${step375SelectedInstance()} · Reference 9"))
        val types = listOf("Vanilla","Forge","NeoForge","Fabric","Quilt","Modpack","Mod","Shader","Resource Pack","World","Other")
        val chips = LinearLayout(this)
        types.forEach { type -> chips.addView(step375Button(type) { when (type) { "Modpack" -> startContentImport("Modpack"); "Mod" -> startContentImport("Mod"); "Shader" -> startContentImport("Shader Pack"); "Resource Pack" -> startContentImport("Resource Pack"); "World" -> startContentImport("World"); "Other" -> android.widget.Toast.makeText(this, "Other content uses the Android file picker when a matching importer is available.", android.widget.Toast.LENGTH_LONG).show(); else -> android.widget.Toast.makeText(this, "$type version catalogue", android.widget.Toast.LENGTH_SHORT).show() } }, LinearLayout.LayoutParams(dp(112), dp(44)).apply { marginEnd = dp(6) }) }
        pageArea.addView(android.widget.HorizontalScrollView(this).apply { isHorizontalScrollBarEnabled = false; addView(chips) }, LinearLayout.LayoutParams(-1, dp(52)))
        listOf("1.21.11","1.21.10","1.21.9","1.20.6","1.20.4","1.18.2","1.16.5").forEach { version -> val p = step375Panel(10); val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }; row.addView(step375Text("▣", 22f, true), LinearLayout.LayoutParams(dp(40), dp(52))); row.addView(step375Text(version, 17f, true), LinearLayout.LayoutParams(0, dp(52), 1f)); val installed = MinecraftVersionInstallManager.isInstalled(this, version); row.addView(step375Button(if (installed) "SELECT" else "INSTALL", installed) { saveMinecraftVersion(version); if (installed) showPage("Home") else installMinecraftVersion(version) }, LinearLayout.LayoutParams(dp(112), dp(44))); p.addView(row); pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(68)).apply { bottomMargin = dp(7) }) }
    }

    private fun step375Settings() {
        pageArea.addView(step375Title("Settings", "Reference 2 · polished renderer-style settings."))
        listOf("Global Renderer" to "Krypton Wrapper","Vulkan Driver" to "Turnip","Graphics API" to "Automatic","Resolution Rule" to "Percentage","Memory" to "Auto").forEach { (n, v) -> val p = step375Panel(12); p.addView(step375Text(n, 16f, true)); p.addView(step375Text(v, 12f).apply { setTextColor(android.graphics.Color.argb(190, 210, 230, 240)) }); p.addView(step375Button("CHANGE") { }); pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(92)).apply { bottomMargin = dp(7) }) }
        val p = step375Panel(12); p.addView(step375Text("Resolution Scale", 16f, true)); p.addView(android.widget.SeekBar(this).apply { max = 150; progress = step375Prefs().getInt("scale", 100); setOnSeekBarChangeListener(object: android.widget.SeekBar.OnSeekBarChangeListener { override fun onProgressChanged(b: android.widget.SeekBar?, value: Int, fromUser: Boolean) { step375Prefs().edit().putInt("scale", value.coerceAtLeast(50)).apply() }; override fun onStartTrackingTouch(b: android.widget.SeekBar?) {}; override fun onStopTrackingTouch(b: android.widget.SeekBar?) {} }) }); pageArea.addView(p, LinearLayout.LayoutParams(-1, dp(88)).apply { bottomMargin = dp(7) })
        val f = step375Panel(12); f.addView(android.widget.Switch(this).apply { text = "Game Fullscreen"; setTextColor(android.graphics.Color.WHITE); isChecked = step375Prefs().getBoolean("fullscreen", true); setOnCheckedChangeListener { _, value -> step375Prefs().edit().putBoolean("fullscreen", value).apply() } }); pageArea.addView(f, LinearLayout.LayoutParams(-1, dp(70)))
    }

    override fun onPause() { try { step375Track?.pause() } catch (_: Throwable) {}; super.onPause() }
    override fun onResume() { super.onResume(); try { if (step375Track?.playState != android.media.AudioTrack.PLAYSTATE_PLAYING) step375Track?.play() } catch (_: Throwable) {} }
    override fun onDestroy() { try { step375Track?.stop(); step375Track?.release() } catch (_: Throwable) {}; step375Track = null; super.onDestroy() }
'''

def method_span(src: str, sig: str):
    start = src.find(sig)
    if start < 0: raise SystemExit(f'[step375] missing method: {sig}')
    brace = src.find('{', start)
    if brace < 0: raise SystemExit(f'[step375] missing opening brace: {sig}')
    depth = 0; quoted = False; escaped = False; triple = False
    i = brace
    while i < len(src):
        c = src[i]; n = src[i+1] if i + 1 < len(src) else ''; n2 = src[i+2] if i + 2 < len(src) else ''
        if triple:
            if c == '"' and n == '"' and n2 == '"': triple = False; i += 3; continue
            i += 1; continue
        if quoted:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': quoted = False
            i += 1; continue
        if c == '"' and n == '"' and n2 == '"': triple = True; i += 3; continue
        if c == '"': quoted = True; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return start, i + 1
        i += 1
    raise SystemExit('[step375] unterminated Kotlin method')

def replace_method(src: str, sig: str, body: str) -> str:
    a, b = method_span(src, sig)
    return src[:a] + body + src[b:]

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    ui = root / UI
    if not ui.is_file(): raise SystemExit(f'[step375] missing UI: {ui}')
    source = ui.read_text(encoding='utf-8')
    source = source.replace('    override fun onCreate(', FIELD_HELP + '\n    override fun onCreate(', 1) if 'private var step375Track:' not in source else source
    source = replace_method(source, '    override fun onCreate(', ONCREATE)
    source = replace_method(source, '    private fun buildUi()', BUILD)
    source = replace_method(source, '    private fun showPage(page: String)', SHOW)
    if 'private fun step375FirstRun()' not in source:
        anchor = source.find('    private fun rendererPage()')
        if anchor < 0: anchor = source.find('    companion object')
        if anchor < 0: raise SystemExit('[step375] insertion anchor missing')
        source = source[:anchor] + PAGES + '\n' + source[anchor:]
    if '"World" -> MinecraftContentManager.Kind.WORLD' not in source:
        source = source.replace('                "Resource Pack" -> MinecraftContentManager.Kind.RESOURCE_PACK\n                else -> null', '                "Resource Pack" -> MinecraftContentManager.Kind.RESOURCE_PACK\n                "World" -> MinecraftContentManager.Kind.WORLD\n                else -> null', 1)
    for sig in ('launchSelectedMinecraft', 'installMinecraftVersion', 'selectedMinecraftVersion', 'showMicrosoftSignInPage', 'openCosmeticImagePicker'):
        if not re.search(r'private\s+fun\s+' + re.escape(sig) + r'\s*\(', source):
            raise SystemExit(f'[step375] required backend helper missing: {sig}')
    ui.write_text(source, encoding='utf-8')
    manifest = root / 'app/src/main/AndroidManifest.xml'
    if manifest.is_file():
        m = manifest.read_text(encoding='utf-8')
        if 'android.permission.INTERNET' not in m:
            i = m.find('>', m.find('<manifest '))
            m = m[:i+1] + '\n    <uses-permission android:name="android.permission.INTERNET" />' + m[i+1:]
            manifest.write_text(m, encoding='utf-8')
    print('[step375] custom UI applied')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
