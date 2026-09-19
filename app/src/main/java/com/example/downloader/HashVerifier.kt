package com.example.downloader

import java.io.File
import java.io.FileInputStream
import java.security.MessageDigest

object HashVerifier {

    fun computeSha1(file: File): String {
        if (!file.exists()) return ""
        val digest = MessageDigest.getInstance("SHA-1")
        FileInputStream(file).use { fis ->
            val buffer = ByteArray(8192)
            var bytesRead: Int
            while (fis.read(buffer).also { bytesRead = it } != -1) {
                digest.update(buffer, 0, bytesRead)
            }
        }
        val bytes = digest.digest()
        val sb = StringBuilder()
        for (b in bytes) {
            sb.append(String.format("%02x", b.toInt() and 0xff))
        }
        return sb.toString()
    }

    fun verifySha1(file: File, expectedSha1: String?): Boolean {
        if (!file.exists()) return false
        if (expectedSha1.isNullOrBlank()) return true // No hash was provided; callers are responsible for size validation.
        val actual = computeSha1(file)
        return actual.equals(expectedSha1, ignoreCase = true)
    }
}
