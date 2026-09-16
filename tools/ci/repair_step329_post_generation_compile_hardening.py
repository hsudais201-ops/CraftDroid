#!/usr/bin/env python3
"""Final generated-tree Kotlin hardening applied after every late UI generator."""
from pathlib import Path
import sys


def one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step329] expected exactly one {name}, found {len(hits)}")
    return hits[0]


def before_class_close(source: str, block: str, marker: str) -> str:
    if marker in source:
        return source
    # Insert before the final top-level class/object brace. These generated activities
    # have no trailing declarations after the class, so the last brace is authoritative.
    pos = source.rfind("}\n")
    if pos < 0:
        raise SystemExit(f"[step329] missing class closing brace for {marker}")
    return source[:pos] + block + "\n" + source[pos:]


SERVER_MARKER = "// STEP329_SERVER_CONTRACTS"
SERVER_BLOCK = r'''

// STEP329_SERVER_CONTRACTS
private fun serverPrefs(): android.content.SharedPreferences =
    getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)

private fun getSavedServers(): List<Pair<String, Int>> {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    return (0 until count).mapNotNull { index ->
        val host = prefs.getString("host_$index", "")?.trim().orEmpty()
        if (host.isBlank()) null else host to prefs.getInt("port_$index", 25565).coerceIn(1, 65535)
    }
}

private fun getServerName(index: Int): String =
    serverPrefs().getString("name_$index", "")?.trim().orEmpty()

private fun getServerStatus(host: String, port: Int): String =
    serverPrefs().getString("status_$host:$port", "Unknown") ?: "Unknown"

private fun selectServer(host: String, port: Int) {
    getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
        .putString("selected_server", "$host:$port")
        .apply()
    refreshServerStatus(host, port)
}

private fun deleteServer(index: Int) {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    if (index !in 0 until count) return
    val edit = prefs.edit()
    for (i in index until count - 1) {
        edit.putString("host_$i", prefs.getString("host_${i + 1}", "") ?: "")
            .putInt("port_$i", prefs.getInt("port_${i + 1}", 25565))
            .putString("name_$i", prefs.getString("name_${i + 1}", "") ?: "")
    }
    edit.remove("host_${count - 1}")
        .remove("port_${count - 1}")
        .remove("name_${count - 1}")
        .putInt("count", count - 1)
        .apply()
}

private fun showServerDialog(index: Int) {
    val prefs = serverPrefs()
    val count = prefs.getInt("count", 0).coerceIn(0, 256)
    val valid = index in 0 until count
    val box = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(dp(24), 0, dp(24), 0)
    }
    val name = android.widget.EditText(this).apply {
        hint = "Server name"
        setSingleLine(true)
        if (valid) setText(prefs.getString("name_$index", "") ?: "")
    }
    val host = android.widget.EditText(this).apply {
        hint = "Address, e.g. play.example.com"
        setSingleLine(true)
        if (valid) setText(prefs.getString("host_$index", "") ?: "")
    }
    val port = android.widget.EditText(this).apply {
        hint = "Port"
        setSingleLine(true)
        inputType = android.text.InputType.TYPE_CLASS_NUMBER
        if (valid) setText(prefs.getInt("port_$index", 25565).toString()) else setText("25565")
    }
    box.addView(name, LinearLayout.LayoutParams(-1, dp(54)))
    box.addView(host, LinearLayout.LayoutParams(-1, dp(54)))
    box.addView(port, LinearLayout.LayoutParams(-1, dp(54)))
    android.app.AlertDialog.Builder(this)
        .setTitle(if (valid) "Edit Server" else "Add Server")
        .setView(box)
        .setNegativeButton("Cancel", null)
        .setPositiveButton("Save") { _, _ ->
            val cleanHost = host.text.toString().trim()
            val cleanName = name.text.toString().trim().ifBlank { cleanHost }
            val cleanPort = port.text.toString().toIntOrNull()?.coerceIn(1, 65535) ?: 25565
            if (cleanHost.isBlank()) {
                Toast.makeText(this, "Server address is required", Toast.LENGTH_LONG).show()
                return@setPositiveButton
            }
            val currentCount = prefs.getInt("count", 0).coerceIn(0, 256)
            val target = if (valid) index else currentCount
            prefs.edit()
                .putInt("count", if (valid) currentCount else currentCount + 1)
                .putString("host_$target", cleanHost)
                .putInt("port_$target", cleanPort)
                .putString("name_$target", cleanName)
                .putString("status_$cleanHost:$cleanPort", "Not checked")
                .apply()
            selectServer(cleanHost, cleanPort)
            showPage("Game")
        }.show()
}

private fun refreshServerStatus(host: String, port: Int) {
    val key = "status_$host:$port"
    serverPrefs().edit().putString(key, "Checking…").apply()
    Thread {
        val status = try {
            java.net.Socket().use { socket ->
                socket.connect(java.net.InetSocketAddress(host, port), 2500)
            }
            "Online"
        } catch (_: Throwable) {
            "Offline"
        }
        runOnUiThread {
            serverPrefs().edit().putString(key, status).apply()
            if (currentPage == "Game") showPage("Game")
        }
    }.start()
}
'''


def add_ui_helpers(source: str) -> str:
    for old in (
        "setTextColor(this@DroidLauncherUiActivity.text)",
        "setTextColor(text)",
    ):
        source = source.replace(old, "setTextColor(primaryText)")
    source = source.replace("singleLine = true", "setSingleLine(true)")
    helpers = r'''
    private fun saveMinecraftVersion(version: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("selected_minecraft_version", version.trim()).apply()
    }

    private fun selectedMinecraftVersion(): String {
        val cached = runCatching { MinecraftLatestVersionManager.getCached(this) }.getOrNull()
        return getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_version", null)?.trim()?.takeIf { it.isNotBlank() }
            ?: cached ?: "1.21.11"
    }

    private fun selectedMinecraftProfile(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_profile", "Default")?.trim().orEmpty().ifBlank { "Default" }
'''
    if "private fun saveMinecraftVersion(version: String)" not in source:
        source = before_class_close(source, helpers, "private fun saveMinecraftVersion(version: String)")
    if SERVER_MARKER not in source:
        source = before_class_close(source, SERVER_BLOCK, SERVER_MARKER)
    return source


def patch_ui(root: Path) -> None:
    path = one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    path.write_text(add_ui_helpers(path.read_text(encoding="utf-8")), encoding="utf-8")


def patch_installer(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = path.read_text(encoding="utf-8")
    if "fun isLaunchReady(context: Context, version: String): Boolean" not in s:
        anchor = "    fun lastError(context: Context, version: String): String? ="
        block = '''    /** Full pre-launch readiness gate for the selected vanilla installation. */
    fun isLaunchReady(context: Context, version: String): Boolean {
        if (!isInstalled(context, version)) return false
        val root = versionRoot(context, version)
        val client = File(root, "$version.jar")
        val metadata = File(root, "$version.json")
        return client.isFile && client.length() > 0L && metadata.isFile && metadata.length() > 0L
    }

'''
        if anchor not in s:
            raise SystemExit("[step329] installer anchor missing for isLaunchReady")
        s = s.replace(anchor, block + anchor, 1)
    if "fun savedProgress(context: Context, version: String): Progress" not in s:
        anchor = "    fun install(context: Context, version: String, listener: Listener? = null) {"
        block = '''    /** Returns persisted progress so the UI can recover after recreation. */
    fun savedProgress(context: Context, version: String): Progress {
        val p = prefs(context)
        return Progress(version, p.getLong(progressKey(version), 0L), p.getLong(totalKey(version), 0L),
            p.getString(stageKey(version), "Ready") ?: "Ready", state(context, version))
    }

'''
        if anchor not in s:
            raise SystemExit("[step329] installer anchor missing for savedProgress")
        s = s.replace(anchor, block + anchor, 1)
    if "ConcurrentHashMap.newKeySet<String>()" not in s:
        s = s.replace("import java.util.concurrent.Executors\n", "import java.util.concurrent.Executors\nimport java.util.concurrent.ConcurrentHashMap\n", 1)
        s = s.replace("    private val executor = Executors.newCachedThreadPool()\n", "    private val executor = Executors.newCachedThreadPool()\n    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n    @Volatile private var progressContext: Context? = null\n", 1)
    if "fun cancel(context: Context, version: String)" not in s:
        anchor = "    fun install(context: Context, version: String, listener: Listener? = null) {"
        block = '''    fun cancel(context: Context, version: String) {
        cancellations.add(version)
        setState(context, version, State.FAILED, "Installation cancelled")
    }

    fun isCancellationRequested(version: String): Boolean = cancellations.contains(version)

'''
        s = s.replace(anchor, block + anchor, 1)
    if "progressContext = context.applicationContext" not in s:
        marker = "        if (isInstalled(context, version)) {\n            listener?.onComplete(version)\n            return\n        }\n"
        if marker in s:
            s = s.replace(marker, marker + "        progressContext = context.applicationContext\n        cancellations.remove(version)\n", 1)
    if "if (isCancellationRequested(version))" not in s:
        marker = "                    while (true) {\n                        val count = input.read(buffer)"
        if marker in s:
            s = s.replace(marker, "                    while (true) {\n                        if (isCancellationRequested(version)) throw java.io.IOException(\"Installation cancelled\")\n                        val count = input.read(buffer)", 1)
    report = "    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {"
    if report in s and "prefs(context).edit()" not in s[s.find(report):s.find(report)+1000]:
        start = s.find(report)
        brace = s.find("{", start)
        depth = 0
        end = -1
        for i in range(brace, len(s)):
            if s[i] == "{": depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        if end < 0:
            raise SystemExit("[step329] report function unterminated")
        body = '''    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {
        progressContext?.let { context ->
            prefs(context).edit()
                .putLong(progressKey(version), downloaded.coerceAtLeast(0L))
                .putLong(totalKey(version), total.coerceAtLeast(0L))
                .putString(stageKey(version), stage)
                .apply()
        }
        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))
    }'''
        s = s[:start] + body + s[end:]
    if "private fun progressKey(version: String)" not in s:
        pos = s.rfind("\n}")
        if pos < 0: raise SystemExit("[step329] installer close missing")
        s = s[:pos] + '''\n    private fun progressKey(version: String) = "mc_install_${version}_downloaded"
    private fun totalKey(version: String) = "mc_install_${version}_total"
    private fun stageKey(version: String) = "mc_install_${version}_stage"
''' + s[pos:]
    path.write_text(s, encoding="utf-8")


def patch_tuner(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftPerformanceTuner.kt")
    s = path.read_text(encoding="utf-8")
    old = '''            val (renderDistance, simulationDistance, graphics, particles, clouds, entityShadows) = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> listOf(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> listOf(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> listOf(14, 8, "fancy", "all", "true", "true")
            }
'''
    new = '''            data class TierSettings(val renderDistance: Int, val simulationDistance: Int, val graphics: String,
                                     val particles: String, val clouds: String, val entityShadows: String)
            val settings = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> TierSettings(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> TierSettings(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> TierSettings(14, 8, "fancy", "all", "true", "true")
            }
            val renderDistance = settings.renderDistance
            val simulationDistance = settings.simulationDistance
            val graphics = settings.graphics
            val particles = settings.particles
            val clouds = settings.clouds
            val entityShadows = settings.entityShadows
'''
    if old in s: s = s.replace(old, new, 1)
    path.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    patch_installer(root)
    patch_ui(root)
    patch_tuner(root)
    print("[step329] final generated UI contracts restored after all late generators")
    print("[step329] text-color and EditText single-line APIs normalized")
    print("[step329] installer readiness/progress/cancellation contracts restored")
    print("[step329] typed performance tier settings restored")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
