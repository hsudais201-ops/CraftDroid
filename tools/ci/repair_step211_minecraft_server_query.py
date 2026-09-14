#!/usr/bin/env python3
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step211] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    if "private fun getSavedServer(): Pair<String, Int>?" not in s:
        anchor = "    private fun getSavedServers(): List<Pair<String, Int>> {"
        compat = '''    private fun getSavedServer(): Pair<String, Int>? {
        val selected = loadServerPrefs().getString("selected_server", null)
        val list = getSavedServers()
        if (selected != null) {
            val x = selected.split(":", limit = 2)
            val p = if (x.size == 2) x[1].toIntOrNull() else null
            if (p != null) return x[0] to p
        }
        return list.firstOrNull()
    }

'''
        if anchor not in s: raise SystemExit("[step211] getSavedServers anchor not found")
        s = s.replace(anchor, compat + anchor, 1)
    start = s.find("    private fun getServerStatus(address: String, port: Int): String")
    end = s.find("    private fun rendererPage() {", start)
    if start < 0 or end < 0: raise SystemExit("[step211] server status block not found")
    methods = '''    private fun getServerStatus(address: String, port: Int): String = loadServerPrefs().getString("status_$address:$port", "● Unknown") ?: "● Unknown"

    private fun getServerDetails(address: String, port: Int): String = loadServerPrefs().getString("details_$address:$port", "") ?: ""

    private fun refreshServerStatus(address: String, port: Int) {
        loadServerPrefs().edit().putString("status_$address:$port", "● Checking…").apply()
        if (currentPage == "Game") showPage("Game")
        Thread {
            val details = queryMinecraftStatus(address, port)
            val status = if (details != null) "● Online" else "● Offline"
            loadServerPrefs().edit().putString("status_$address:$port", status).putString("details_$address:$port", details ?: "Unable to query Minecraft status").apply()
            runOnUiThread { if (currentPage == "Game") showPage("Game") }
        }.start()
    }

    private fun queryMinecraftStatus(address: String, port: Int): String? {
        return try {
            java.net.Socket().use { socket ->
                socket.soTimeout = 2500
                socket.connect(java.net.InetSocketAddress(address, port), 2500)
                val out = java.io.DataOutputStream(socket.getOutputStream())
                val input = java.io.DataInputStream(socket.getInputStream())
                val host = address.toByteArray(Charsets.UTF_8)
                val handshake = java.io.ByteArrayOutputStream()
                java.io.DataOutputStream(handshake).also { h ->
                    writeVarInt(h, 0); writeVarInt(h, 47); writeVarInt(h, host.size); h.write(host); h.writeShort(port); writeVarInt(h, 1); h.flush()
                }
                writePacket(out, handshake.toByteArray())
                val request = java.io.ByteArrayOutputStream()
                java.io.DataOutputStream(request).also { r -> writeVarInt(r, 0); r.flush() }
                writePacket(out, request.toByteArray())
                val len = readVarInt(input)
                if (len <= 0 || len > 1024 * 1024) return null
                val bytes = ByteArray(len); input.readFully(bytes)
                val p = java.io.DataInputStream(bytes.inputStream())
                if (readVarInt(p) != 0) return null
                val jsonLen = readVarInt(p)
                if (jsonLen <= 0 || jsonLen > 1024 * 1024) return null
                val jsonBytes = ByteArray(jsonLen); p.readFully(jsonBytes)
                val json = org.json.JSONObject(String(jsonBytes, Charsets.UTF_8))
                val version = json.optJSONObject("version")?.optString("name", "") ?: ""
                val players = json.optJSONObject("players")
                val online = players?.optInt("online", -1) ?: -1
                val max = players?.optInt("max", -1) ?: -1
                val motdValue = json.opt("description")
                val motd = when (motdValue) { is String -> motdValue; is org.json.JSONObject -> motdValue.optString("text", ""); else -> "" }.replace("\\n", " ").trim()
                buildString {
                    if (motd.isNotBlank()) append(motd)
                    if (version.isNotBlank()) { if (isNotEmpty()) append("  ·  "); append(version) }
                    if (online >= 0 && max >= 0) { if (isNotEmpty()) append("  ·  "); append(online).append("/").append(max).append(" players") }
                    if (isEmpty()) append("Minecraft server responded")
                }
            }
        } catch (_: Exception) { null }
    }

    private fun writePacket(out: java.io.DataOutputStream, payload: ByteArray) { writeVarInt(out, payload.size); out.write(payload); out.flush() }

    private fun writeVarInt(out: java.io.DataOutputStream, value: Int) {
        var v = value
        do { var temp = v and 0x7F; v = v ushr 7; if (v != 0) temp = temp or 0x80; out.writeByte(temp) } while (v != 0)
    }

    private fun readVarInt(input: java.io.DataInputStream): Int {
        var result = 0; var shift = 0
        while (shift < 35) { val b = input.readUnsignedByte(); result = result or ((b and 0x7F) shl shift); if ((b and 0x80) == 0) return result; shift += 7 }
        throw java.io.IOException("Invalid VarInt")
    }

'''
    s = s[:start] + methods + s[end:]
    old = 'info.addView(label(server.second.toString() + "  ·  " + getServerStatus(server.first, server.second), 12f, false))'
    new = old + '\n                val details = getServerDetails(server.first, server.second)\n                if (details.isNotBlank()) info.addView(label(details, 11f, false))'
    s = s.replace(old, new, 1)
    marker = '        val addServer = button("+ Add Server", true)'
    if 'serverList.forEach { refreshServerStatus(it.first, it.second) }' not in s:
        s = s.replace(marker, '        serverList.forEach { refreshServerStatus(it.first, it.second) }\n\n' + marker, 1)
    ui.write_text(s, encoding="utf-8")
    print("[step211] Minecraft status protocol query installed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
