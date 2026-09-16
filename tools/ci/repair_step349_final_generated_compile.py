#!/usr/bin/env python3
"""Final compile-boundary repair for the generated launcher UI.

This is intentionally the last source rewrite before the verifier/build. The late
UI generators can append helpers more than once; this pass restores canonical
helpers, deduplicates generated server methods, fixes EditText properties, and
ensures the installer progress context is declared.
"""
from pathlib import Path
import re
import sys

JAVA_HELPERS = '''    private fun recommendedJavaForVersion(version: String): Int {
        val nums = version.split('.').mapNotNull { it.toIntOrNull() }
        val major = nums.getOrNull(0) ?: return 17
        val minor = nums.getOrNull(1) ?: 0
        val patch = nums.getOrNull(2) ?: 0
        return when {
            major == 1 && minor <= 16 -> 8
            major == 1 && minor <= 19 -> 17
            major == 1 && minor == 20 && patch < 5 -> 17
            major == 1 && (minor > 20 || (minor == 20 && patch >= 5)) -> 21
            major >= 25 -> 25
            else -> 21
        }
    }

    private fun storedJavaOverride(): Int? {
        val raw = getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_java_runtime", "auto") ?: "auto"
        return raw.removePrefix("Internal-").toIntOrNull()
    }

    private fun resolveJavaForVersion(version: String): Int =
        storedJavaOverride() ?: recommendedJavaForVersion(version)

    private fun saveJavaOverride(value: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit()
            .putString("selected_java_runtime", value)
            .apply()
        System.setProperty("droid.launcher.java.runtime", value)
    }

    private fun getResolvedJavaForLaunch(version: String): Int = resolveJavaForVersion(version)

'''

SERVER_HELPERS = '''    private fun serverPrefs(): android.content.SharedPreferences =
        getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)

    private fun getSavedServers(): List<Pair<String, Int>> {
        val prefs = serverPrefs()
        val count = prefs.getInt("count", 0).coerceIn(0, 256)
        return (0 until count).mapNotNull { i ->
            val host = prefs.getString("host_$i", "")?.trim().orEmpty()
            val port = prefs.getInt("port_$i", 25565)
            if (host.isBlank()) null else host to port.coerceIn(1, 65535)
        }
    }

    private fun getServerName(index: Int): String =
        serverPrefs().getString("name_$index", "")?.trim().orEmpty()

    private fun getServerStatus(host: String, port: Int): String =
        serverPrefs().getString("status_${host}:$port", "Unknown") ?: "Unknown"

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


def brace_end(text: str, start: int) -> int:
    brace = text.find('{', start)
    if brace < 0:
        raise ValueError('missing opening brace')
    depth = 0
    string = triple = char = line = block = False
    escaped = False
    i = brace
    while i < len(text):
        c = text[i]
        n = text[i + 1] if i + 1 < len(text) else ''
        n2 = text[i + 2] if i + 2 < len(text) else ''
        if line:
            if c == '\n': line = False
            i += 1; continue
        if block:
            if c == '*' and n == '/': block = False; i += 2; continue
            i += 1; continue
        if triple:
            if c == '"' and n == '"' and n2 == '"': triple = False; i += 3; continue
            i += 1; continue
        if string:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': string = False
            i += 1; continue
        if char:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == "'": char = False
            i += 1; continue
        if c == '/' and n == '/': line = True; i += 2; continue
        if c == '/' and n == '*': block = True; i += 2; continue
        if c == '"' and n == '"' and n2 == '"': triple = True; i += 3; continue
        if c == '"': string = True; i += 1; continue
        if c == "'": char = True; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i + 1
        i += 1
    raise ValueError('unterminated body')


def line_end(text: str, start: int) -> int:
    end = text.find('\n', start)
    return len(text) if end < 0 else end + 1


def remove_decl(text: str, signature: str) -> str:
    while True:
        start = text.find(signature)
        if start < 0: return text
        end = line_end(text, start) if re.search(r'\)\s*:', signature) or signature.rstrip().endswith(')') and signature.count('fun ') == 1 and '{' not in text[start:line_end(text,start)] else brace_end(text, start)
        text = text[:start] + text[end:]


def remove_named_method(text: str, name: str) -> str:
    pat = re.compile(r'(?m)^\s*private\s+fun\s+' + re.escape(name) + r'\s*\(')
    while True:
        m = pat.search(text)
        if not m: return text
        end = brace_end(text, m.start())
        text = text[:m.start()] + text[end:]


def remove_expression_method(text: str, name: str) -> str:
    pat = re.compile(r'(?m)^\s*private\s+fun\s+' + re.escape(name) + r'\s*\([^\n]*\)\s*:\s*[^\n=]+\s*=')
    while True:
        m = pat.search(text)
        if not m: return text
        end = line_end(text, m.start())
        text = text[:m.start()] + text[end:]


def restore_java_helpers(text: str) -> str:
    for name in ('recommendedJavaForVersion','storedJavaOverride','saveJavaOverride'):
        text = remove_named_method(text, name)
    for name in ('resolveJavaForVersion','getResolvedJavaForLaunch'):
        text = remove_expression_method(text, name)
    anchor = text.find('    private fun rendererPage() {')
    if anchor < 0: anchor = text.find('    private fun controlsPage() {')
    if anchor < 0: raise SystemExit('[step349] Java helper insertion anchor missing')
    return text[:anchor] + JAVA_HELPERS + text[anchor:]


def restore_server_helpers(text: str) -> str:
    for name in ('serverPrefs','getSavedServers','getServerName','getServerStatus','selectServer','deleteServer','showServerDialog','refreshServerStatus'):
        text = remove_named_method(text, name) if name not in ('serverPrefs','getServerName','getServerStatus') else remove_expression_method(text, name)
    anchor = text.find('    private fun refreshLatestMinecraftVersion()')
    if anchor < 0: anchor = text.find('    private fun minecraftVersionChoices()')
    if anchor < 0: raise SystemExit('[step349] server helper insertion anchor missing')
    return text[:anchor] + SERVER_HELPERS + text[anchor:]


def repair_orphan_fragments(text: str) -> str:
    text = re.sub(r'(?m)^\s*storedJavaOverride\(\) \?: recommendedJavaForVersion\(version\)\s*$\n', '', text)
    legacy = text.find('val saved = getSharedPreferences("droid_launcher", MODE_PRIVATE).getInt("java_runtime_override", 0)')
    feature = text.find('    private fun featuresPage() {', legacy if legacy >= 0 else 0)
    if legacy >= 0 and feature > legacy:
        text = text[:legacy] + text[feature:]
    return text


def repair_string_newlines(text: str) -> tuple[str, int]:
    out=[]; i=0; changed=0; string=triple=char=line=block=False; escaped=False
    while i < len(text):
        c=text[i]; n=text[i+1] if i+1<len(text) else ''; n2=text[i+2] if i+2<len(text) else ''
        if line:
            out.append(c); line = c != '\n'; i += 1; continue
        if block:
            out.append(c)
            if c=='*' and n=='/': out.append('/'); i+=2; block=False
            else: i+=1
            continue
        if triple:
            out.append(c)
            if c=='"' and n=='"' and n2=='"': out.extend(['"','"']); i+=3; triple=False
            else: i+=1
            continue
        if string:
            if escaped: out.append(c); escaped=False; i+=1; continue
            if c=='\\': out.append(c); escaped=True; i+=1; continue
            if c=='"': out.append(c); string=False; i+=1; continue
            if c=='\n': out.append('\\n'); changed+=1; i+=1; continue
            out.append(c); i+=1; continue
        if char:
            out.append(c)
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c=="'": char=False
            i+=1; continue
        if c=='/' and n=='/': out.extend([c,n]); line=True; i+=2; continue
        if c=='/' and n=='*': out.extend([c,n]); block=True; i+=2; continue
        if c=='"' and n=='"' and n2=='"': out.extend(['"','"','"']); triple=True; i+=3; continue
        if c=='"': out.append(c); string=True; i+=1; continue
        if c=="'": out.append(c); char=True; i+=1; continue
        out.append(c); i+=1
    if string: raise ValueError('unterminated Kotlin string')
    return ''.join(out), changed


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv)>1 else 'droid-src').resolve()
    ui = root/'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    manager = root/'app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt'
    if not ui.is_file(): raise SystemExit(f'[step349] missing UI source: {ui}')
    if not manager.is_file(): raise SystemExit(f'[step349] missing installer source: {manager}')

    source = ui.read_text(encoding='utf-8')
    before = source
    source = repair_orphan_fragments(source)
    source = restore_java_helpers(source)
    source = restore_server_helpers(source)
    source = source.replace('.apply { setText(accountName(index)); singleLine = true; hint = "Profile name" }', '.apply { setText(accountName(index)); setSingleLine(true); hint = "Profile name" }')
    source = source.replace('; singleLine = true }', '; setSingleLine(true) }')
    source = source.replace('; singleLine = false }', '; setSingleLine(false) }')
    source, string_changes = repair_string_newlines(source)
    ui.write_text(source, encoding='utf-8')

    m = manager.read_text(encoding='utf-8')
    if 'private var progressContext: Context? = null' not in m:
        anchor = '    private val cancellations = ConcurrentHashMap.newKeySet<String>()'
        if anchor not in m: raise SystemExit('[step349] installer cancellation anchor missing')
        m = m.replace(anchor, anchor + '\n    private var progressContext: Context? = null', 1)
    manager.write_text(m, encoding='utf-8')

    # Structural invariants: each generated server helper must exist exactly once.
    checks = [
        'private fun serverPrefs()', 'private fun getSavedServers()', 'private fun getServerName(',
        'private fun getServerStatus(', 'private fun selectServer(', 'private fun deleteServer(',
        'private fun showServerDialog(', 'private fun refreshServerStatus(',
    ]
    for sig in checks:
        count = source.count(sig)
        if count != 1: raise SystemExit(f'[step349] {sig} count={count}, expected 1')
    if source.count('singleLine ='):
        raise SystemExit('[step349] raw EditText singleLine assignments remain')
    if m.count('progressContext') < 3:
        raise SystemExit('[step349] progressContext contract unexpectedly incomplete')

    print(f'[step349] deterministic final source repair complete; changed={int(source != before)} string_fixes={string_changes}')
    print('[step349] canonical server helper set count=1')
    print('[step349] canonical Java resolver helper set restored')
    print('[step349] installer progressContext declared and assigned')
    print('[step349] EditText singleLine mappings normalized')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
