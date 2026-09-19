package com.example.auth

enum class AccountProviderType(
    val id: String,
    val displayName: String,
    val isOfficiallyAuthenticated: Boolean
) {
    MICROSOFT(
        id = "MICROSOFT",
        displayName = "Microsoft",
        isOfficiallyAuthenticated = true
    ),
    ELY_BY(
        id = "ELY_BY",
        displayName = "Ely.by",
        isOfficiallyAuthenticated = true
    ),
    LOCAL_TEST(
        id = "LOCAL_TEST",
        displayName = "Offline / Local",
        isOfficiallyAuthenticated = false
    );

    companion object {
        fun fromId(id: String?): AccountProviderType {
            return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: LOCAL_TEST
        }
    }
}
