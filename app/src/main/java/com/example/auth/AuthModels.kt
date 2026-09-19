package com.example.auth

data class DeviceCodeResponse(
    val deviceCode: String,
    val userCode: String,
    val verificationUri: String,
    val expiresIn: Int,
    val interval: Int,
    val message: String
)

data class MicrosoftTokenResponse(
    val accessToken: String,
    val refreshToken: String,
    val expiresIn: Int
)

data class MinecraftAuthResult(
    val uuid: String,
    val username: String,
    val accessToken: String,
    val userHash: String,
    val skinUrl: String? = null,
    val expiresIn: Int
)

sealed class AuthState {
    data object Idle : AuthState()
    data class DeviceCodePrompt(val userCode: String, val verificationUri: String, val message: String) : AuthState()
    data class Polling(val message: String) : AuthState()
    data class Authenticating(val step: String) : AuthState()
    data class Success(val username: String, val uuid: String) : AuthState()
    data class Error(val message: String) : AuthState()
}
