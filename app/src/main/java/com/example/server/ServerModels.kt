package com.example.server

data class SavedServer(
    val id: String,
    val name: String,
    val host: String,
    val port: Int = 25565
)

enum class ServerAvailability { LOADING, ONLINE, OFFLINE }

data class ServerStatus(
    val serverId: String,
    val availability: ServerAvailability = ServerAvailability.LOADING,
    val motd: String = "",
    val playersOnline: Int = 0,
    val playersMax: Int = 0,
    val pingMs: Long? = null,
    val version: String = "",
    val iconBase64: String? = null,
    val error: String? = null
)
