package com.example.server

import java.io.ByteArrayOutputStream
import java.io.DataInputStream
import java.io.DataOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import org.json.JSONObject
import kotlin.math.max

object MinecraftServerPing {
    fun ping(server: SavedServer): ServerStatus {
        return try {
            Socket().use { socket ->
                socket.soTimeout = 3500
                socket.connect(InetSocketAddress(server.host, server.port), 2500)
                val out = DataOutputStream(socket.getOutputStream())
                val input = DataInputStream(socket.getInputStream())
                val handshake = ByteArrayOutputStream().also { buffer ->
                    writeVarInt(buffer, 760)
                    writeString(buffer, server.host)
                    DataOutputStream(buffer).writeShort(server.port)
                    writeVarInt(buffer, 1)
                }
                writePacket(out, 0x00, handshake.toByteArray())
                writePacket(out, 0x00, ByteArray(0))

                val statusPacket = readPacket(input) ?: error("No status response")
                if (statusPacket.id != 0x00) error("Unexpected status packet " + statusPacket.id)
                val statusJson = readString(statusPacket.data.inputStream())
                val json = JSONObject(statusJson)
                val players = json.optJSONObject("players")
                val motd = flattenMotd(json.opt("description")).ifBlank { "No MOTD" }

                val pingStart = System.currentTimeMillis()
                writePacket(out, 0x01, longBytes(pingStart))
                val pong = readPacket(input)
                val pingMs = pong?.takeIf { it.id == 0x01 }?.let {
                    max(0L, System.currentTimeMillis() - pingStart)
                }

                ServerStatus(
                    serverId = server.id,
                    availability = ServerAvailability.ONLINE,
                    motd = motd,
                    playersOnline = players?.optInt("online", 0) ?: 0,
                    playersMax = players?.optInt("max", 0) ?: 0,
                    pingMs = pingMs,
                    version = json.optJSONObject("version")?.optString("name").orEmpty(),
                    iconBase64 = json.optString("favicon").ifBlank { null }
                )
            }
        } catch (t: Throwable) {
            ServerStatus(
                serverId = server.id,
                availability = ServerAvailability.OFFLINE,
                error = t.message ?: "Server unreachable"
            )
        }
    }

    private data class Packet(val id: Int, val data: ByteArray)

    private fun writePacket(out: DataOutputStream, packetId: Int, payload: ByteArray) {
        val body = ByteArrayOutputStream()
        writeVarInt(body, packetId)
        body.write(payload)
        val bodyBytes = body.toByteArray()
        writeVarInt(out, bodyBytes.size)
        out.write(bodyBytes)
        out.flush()
    }

    private fun readPacket(input: DataInputStream): Packet? {
        val length = readVarInt(input)
        if (length < 0 || length > 1_048_576) return null
        val packet = ByteArray(length)
        input.readFully(packet)
        val source = packet.inputStream().buffered()
        val id = readVarInt(source)
        val remaining = ByteArray(source.available())
        source.read(remaining)
        return Packet(id, remaining)
    }

    private fun writeString(out: ByteArrayOutputStream, value: String) {
        val bytes = value.toByteArray(Charsets.UTF_8)
        writeVarInt(out, bytes.size)
        out.write(bytes)
    }

    private fun readString(input: java.io.InputStream): String {
        val length = readVarInt(input)
        require(length in 0..1_000_000) { "Invalid string length" }
        return ByteArray(length).also { input.read(it) }.toString(Charsets.UTF_8)
    }

    private fun readVarInt(input: java.io.InputStream): Int {
        var result = 0
        var shift = 0
        while (shift <= 35) {
            val value = input.read()
            if (value < 0) error("Unexpected end of packet")
            result = result or ((value and 0x7F) shl shift)
            if ((value and 0x80) == 0) return result
            shift += 7
        }
        error("Malformed VarInt")
    }

    private fun writeVarInt(out: Any, value: Int) {
        var v = value
        while (true) {
            if ((v and 0x7F.inv()) == 0) {
                when (out) {
                    is ByteArrayOutputStream -> out.write(v)
                    is DataOutputStream -> out.write(v)
                }
                return
            }
            when (out) {
                is ByteArrayOutputStream -> out.write((v and 0x7F) or 0x80)
                is DataOutputStream -> out.write((v and 0x7F) or 0x80)
            }
            v = v ushr 7
        }
    }

    private fun longBytes(value: Long): ByteArray =
        ByteArray(8) { index -> (value ushr ((7 - index) * 8)).toByte() }

    private fun flattenMotd(value: Any?): String {
        return when (value) {
            is String -> value
            is JSONObject -> {
                val builder = StringBuilder()
                builder.append(value.optString("text"))
                val extra = value.optJSONArray("extra")
                if (extra != null) for (i in 0 until extra.length()) {
                    builder.append(flattenMotd(extra.opt(i)))
                }
                builder.toString()
            }
            else -> ""
        }
    }
}
