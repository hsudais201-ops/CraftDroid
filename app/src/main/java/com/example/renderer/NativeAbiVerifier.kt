package com.example.renderer

import android.os.Build
import com.example.logs.LauncherLogger
import java.io.File
import java.io.RandomAccessFile

/**
 * Verifies that bundled Android ELF shared objects match the device ABI.
 *
 * Android may happily unpack an ELF file for another CPU architecture, but
 * dlopen() will then fail later with an UnsatisfiedLinkError/ELF-class error.
 * Catching that before the embedded JVM starts gives the launcher a clear
 * diagnosis and prevents selecting a desktop or wrong-ABI native library.
 */
object NativeAbiVerifier {
    data class Result(
        val valid: Boolean,
        val expectedAbi: String,
        val checked: Int,
        val invalid: List<String>,
        val details: String
    )

    fun verify(directory: File, abi: String = currentAbi()): Result {
        if (!directory.isDirectory) {
            return Result(false, abi, 0, emptyList(), "Native directory does not exist: ${directory.absolutePath}")
        }

        val files = directory.walkTopDown()
            .filter { it.isFile && it.extension.equals("so", true) }
            .toList()

        val invalid = mutableListOf<String>()
        var checked = 0
        for (file in files) {
            val machine = readMachine(file)
            if (machine == null) {
                invalid += "${file.name}: not a valid ELF shared library"
                continue
            }
            checked++
            if (!matches(abi, machine.first, machine.second)) {
                invalid += "${file.name}: ELF${if (machine.first == 2) "64" else "32"} machine=${machine.second}, expected $abi"
            }
        }

        val valid = invalid.isEmpty() && (files.isEmpty() || checked == files.size)
        val details = if (valid) {
            "ABI=$abi; checked=$checked ELF shared libraries"
        } else {
            "ABI=$abi; checked=$checked/${files.size}; invalid=${invalid.joinToString(" | ")}"
        }
        LauncherLogger.info("Native ABI validation: $details")
        return Result(valid, abi, checked, invalid, details)
    }

    fun currentAbi(): String {
        val abi = Build.SUPPORTED_ABIS.firstOrNull()?.lowercase().orEmpty()
        return when {
            abi == "arm64-v8a" || abi.contains("aarch64") -> "arm64-v8a"
            abi == "armeabi-v7a" || abi.contains("armeabi") -> "armeabi-v7a"
            abi == "x86_64" -> "x86_64"
            abi == "x86" -> "x86"
            else -> abi.ifBlank { "unknown" }
        }
    }

    private fun readMachine(file: File): Pair<Int, Int>? = runCatching {
        RandomAccessFile(file, "r").use { raf ->
            val ident = ByteArray(16)
            raf.readFully(ident)
            if (ident[0].toInt() and 0xff != 0x7f ||
                ident[1].toInt() and 0xff != 'E'.code ||
                ident[2].toInt() and 0xff != 'L'.code ||
                ident[3].toInt() and 0xff != 'F'.code) return null

            val elfClass = ident[4].toInt() and 0xff
            val dataEncoding = ident[5].toInt() and 0xff
            if ((elfClass != 1 && elfClass != 2) || dataEncoding != 1) return null

            raf.seek(18L)
            val lo = raf.read()
            val hi = raf.read()
            if (lo < 0 || hi < 0) return null
            val machine = lo or (hi shl 8)
            elfClass to machine
        }
    }.getOrNull()

    private fun matches(abi: String, elfClass: Int, machine: Int): Boolean = when (abi) {
        "arm64-v8a" -> elfClass == 2 && machine == 183   // EM_AARCH64
        "armeabi-v7a" -> elfClass == 1 && machine == 40  // EM_ARM
        "x86_64" -> elfClass == 2 && machine == 62      // EM_X86_64
        "x86" -> elfClass == 1 && machine == 3           // EM_386
        else -> false
    }
}
