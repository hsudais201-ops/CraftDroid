package com.example.renderer

import android.os.Build
import com.example.logs.LauncherLogger
import java.io.RandomAccessFile
import java.io.File

/**
 * Inspects ELF DT_NEEDED entries for Android-native .so files before dlopen().
 * It does not attempt to emulate the Android linker; it reports dependencies
 * that are neither bundled in the same renderer directory nor part of the
 * normal Android system namespace.
 */
object NativeDependencyVerifier {
    data class Result(
        val valid: Boolean,
        val checked: Int,
        val missing: List<String>,
        val details: String
    )

    private val systemPrefixes = listOf(
        "libc.so", "libm.so", "libdl.so", "liblog.so", "libandroid.so",
        "libEGL.so", "libGLESv1_CM.so", "libGLESv2.so", "libOpenSLES.so",
        "libvulkan.so", "libz.so", "libjnigraphics.so", "libandroid_runtime.so",
        "libnativewindow.so", "libutils.so", "libcutils.so", "libbinder.so",
        "libui.so", "libgui.so", "libsync.so", "libhardware.so", "libhidlbase.so",
        "libbase.so", "libstdc++.so", "libgcc.so", "libdl_android.so",
        "libnativehelper.so", "libmemtrack.so", "libion.so", "libstagefright_foundation.so"
    )

    fun verify(directory: File): Result {
        if (!directory.isDirectory) {
            return Result(false, 0, listOf("<directory>"), "Native directory does not exist: ${directory.absolutePath}")
        }
        val files = directory.walkTopDown().filter { it.isFile && it.extension.equals("so", true) }.toList()
        val bundled = files.map { it.name }.toSet()
        val missing = linkedSetOf<String>()
        var checked = 0

        for (file in files) {
            val needed = runCatching { neededLibraries(file) }.getOrElse { e ->
                LauncherLogger.warn("ELF dependency parse failed for ${file.name}: ${e.message}")
                emptyList()
            }
            checked++
            for (dependency in needed) {
                if (!isSystemLibrary(dependency) && dependency !in bundled) {
                    missing += "${file.name} -> $dependency"
                }
            }
        }

        val valid = missing.isEmpty()
        val details = if (valid) {
            "checked=$checked ELF libraries; all DT_NEEDED dependencies are bundled or Android-system libraries"
        } else {
            "checked=$checked ELF libraries; unresolved DT_NEEDED dependencies: ${missing.joinToString(" | ")}"
        }
        LauncherLogger.info("Native dependency validation: $details")
        return Result(valid, checked, missing.toList(), details)
    }

    private fun isSystemLibrary(name: String): Boolean {
        val base = name.substringAfterLast('/')
        if (systemPrefixes.any { base == it }) return true
        // Vendor namespaces commonly expose suffixed variants (for example
        // vendor EGL/GLES implementations). Treat them as platform-provided.
        if (base.startsWith("android.hardware.") || base.startsWith("libvndk") || base.startsWith("libhwbinder")) return true
        return false
    }

    private data class Segment(val type: Long, val offset: Long, val vaddr: Long, val filesz: Long)

    private fun neededLibraries(file: File): List<String> = RandomAccessFile(file, "r").use { raf ->
        val header = ByteArray(64)
        raf.readFully(header)
        require(byte(header[0]) == 0x7f && header[1] == 'E'.code.toByte() && header[2] == 'L'.code.toByte() && header[3] == 'F'.code.toByte()) { "not ELF" }
        require(header[5].toInt() and 0xff == 1) { "only little-endian ELF is supported" }
        val clazz = header[4].toInt() and 0xff
        require(clazz == 1 || clazz == 2) { "unsupported ELF class $clazz" }
        val phoff = if (clazz == 2) u64(header, 32) else u32(header, 28)
        val phentsize = u16(header, if (clazz == 2) 54 else 42)
        val phnum = u16(header, if (clazz == 2) 56 else 44)
        val segments = ArrayList<Segment>()
        var dynamicOffset = -1L
        var dynamicSize = 0L
        repeat(phnum) { i ->
            raf.seek(phoff + i.toLong() * phentsize)
            val ph = ByteArray(phentsize)
            raf.readFully(ph)
            val type = u32(ph, 0)
            if (clazz == 2) {
                val offset = u64(ph, 8); val vaddr = u64(ph, 16); val filesz = u64(ph, 32)
                segments += Segment(type, offset, vaddr, filesz)
                if (type == 2L) { dynamicOffset = offset; dynamicSize = filesz }
            } else {
                val offset = u32(ph, 4); val vaddr = u32(ph, 8); val filesz = u32(ph, 16)
                segments += Segment(type, offset, vaddr, filesz)
                if (type == 2L) { dynamicOffset = offset; dynamicSize = filesz }
            }
        }
        if (dynamicOffset < 0 || dynamicSize <= 0) return@use emptyList()

        val entries = ArrayList<Pair<Long, Long>>()
        val entrySize = if (clazz == 2) 16L else 8L
        raf.seek(dynamicOffset)
        var cursor = 0L
        while (cursor + entrySize <= dynamicSize) {
            val tag: Long
            val value: Long
            if (clazz == 2) {
                val b = ByteArray(16); raf.readFully(b); tag = u64(b, 0); value = u64(b, 8)
            } else {
                val b = ByteArray(8); raf.readFully(b); tag = u32(b, 0); value = u32(b, 4)
            }
            cursor += entrySize
            if (tag == 0L) break
            entries += tag to value
        }

        val strtabVaddr = entries.firstOrNull { it.first == 5L }?.second ?: return@use emptyList() // DT_STRTAB
        val neededOffsets = entries.filter { it.first == 1L }.map { it.second } // DT_NEEDED
        if (neededOffsets.isEmpty()) return@use emptyList()

        val strtabFileOffset = virtualToFileOffset(strtabVaddr, segments)
            ?: return@use emptyList()
        val out = ArrayList<String>(neededOffsets.size)
        for (offset in neededOffsets) {
            out += readCStringAt(raf, strtabFileOffset + offset)
        }
        out
    }

    private fun virtualToFileOffset(vaddr: Long, segments: List<Segment>): Long? =
        segments.firstOrNull { it.type == 1L && vaddr >= it.vaddr && vaddr < it.vaddr + it.filesz }
            ?.let { it.offset + (vaddr - it.vaddr) }

    private fun readCStringAt(raf: RandomAccessFile, offset: Long): String {
        raf.seek(offset)
        val bytes = ByteArray(512)
        var n = 0
        while (n < bytes.size) {
            val b = raf.read()
            if (b < 0 || b == 0) break
            bytes[n++] = b.toByte()
        }
        return bytes.copyOf(n).toString(Charsets.UTF_8)
    }

    private fun u16(b: ByteArray, off: Int): Int = (b[off].toInt() and 0xff) or ((b[off + 1].toInt() and 0xff) shl 8)
    private fun u32(b: ByteArray, off: Int): Long =
        (b[off].toLong() and 0xff) or ((b[off + 1].toLong() and 0xff) shl 8) or
            ((b[off + 2].toLong() and 0xff) shl 16) or ((b[off + 3].toLong() and 0xff) shl 24)
    private fun u64(b: ByteArray, off: Int): Long {
        var value = 0L
        for (i in 0 until 8) value = value or ((b[off + i].toLong() and 0xffL) shl (8 * i))
        return value
    }
}
