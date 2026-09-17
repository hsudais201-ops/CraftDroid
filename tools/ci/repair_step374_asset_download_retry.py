#!/usr/bin/env python3
"""Harden Minecraft asset downloads against transient zero/short HTTP bodies.

The launcher already resumes .part files and verifies Mojang SHA-1/size metadata,
but a transient empty response can currently fail immediately with e.g. 0/8016.
This repair wraps the generated installer with bounded retries while preserving
strict size/hash verification and resumable downloads.
"""
from __future__ import annotations

from pathlib import Path
import re
import sys


NEW_BODY = r'''    private fun downloadResumable(task: DownloadTask, version: String, onProgress: (Long, Long) -> Unit) {
        task.target.parentFile?.let { parent ->
            if (!parent.exists() && !parent.mkdirs() && !parent.isDirectory) {
                throw IOException("Could not create directory ${parent.absolutePath} for ${task.label}")
            }
        }
        if (isArtifactHealthy(task.target, task.sha1, task.size)) {
            onProgress(task.target.length(), task.size.coerceAtLeast(task.target.length()))
            return
        }

        val parent = task.target.parentFile ?: throw IOException("Missing parent directory for ${task.target}")
        val part = File(parent, task.target.name + ".part")
        if (task.size > 0L && part.isFile && part.length() > task.size) part.delete()

        var lastError: Throwable? = null
        repeat(4) { attempt ->
            var resume = if (part.isFile) part.length() else 0L
            if (task.size > 0L && resume >= task.size) resume = 0L
            var connection: HttpURLConnection? = null
            try {
                connection = openDownloadConnection(task.url, resume)
                var responseCode = connection.responseCode
                if (resume > 0L && responseCode != HttpURLConnection.HTTP_PARTIAL) {
                    connection.disconnect()
                    connection = openDownloadConnection(task.url, 0L)
                    resume = 0L
                    if (part.exists() && !part.delete()) throw IOException("Could not reset incomplete download for ${task.label}")
                    responseCode = connection.responseCode
                }

                if (responseCode !in 200..299) {
                    throw IOException("Download failed: HTTP $responseCode for ${task.label}")
                }

                val append = resume > 0L && responseCode == HttpURLConnection.HTTP_PARTIAL
                if (!append) resume = 0L

                val expectedTotal = when {
                    task.size > 0L -> task.size
                    append -> resume + connection.contentLengthLong.coerceAtLeast(0L)
                    connection.contentLengthLong > 0L -> connection.contentLengthLong
                    else -> -1L
                }

                BufferedInputStream(connection.inputStream, BUFFER_SIZE).use { input ->
                    FileOutputStream(part, append).use { output ->
                        val buffer = ByteArray(BUFFER_SIZE)
                        var downloaded = resume
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            if (count == 0) continue
                            output.write(buffer, 0, count)
                            downloaded += count
                            onProgress(downloaded, expectedTotal)
                        }
                        output.fd.sync()
                    }
                }

                if (expectedTotal > 0L && part.length() != expectedTotal) {
                    throw IOException("Incomplete download for ${task.label}: ${part.length()}/$expectedTotal")
                }
                if (!isArtifactHealthy(part, task.sha1, task.size)) {
                    throw IOException("SHA-1 verification failed for ${task.label}")
                }

                finalizeVerifiedFile(part, task.target, task.label, task.sha1, task.size)
                return
            } catch (t: Throwable) {
                lastError = t
                if (attempt + 1 < 4) {
                    Thread.sleep(500L * (attempt + 1))
                }
            } finally {
                connection?.disconnect()
            }
        }
        throw IOException("Download could not be completed for ${task.label} after 4 attempts", lastError)
    }
'''


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    matches = list((root / "app/src/main/java").rglob("MinecraftVersionInstallManager.kt"))
    if len(matches) != 1:
        raise SystemExit(f"[step374] expected exactly one MinecraftVersionInstallManager.kt, found {len(matches)}")
    path = matches[0]
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"    private fun downloadResumable\(task: DownloadTask, version: String, onProgress: \(Long, Long\) -> Unit\) \{.*?\n    \}\n\n    private fun openDownloadConnection", re.S)
    replacement = NEW_BODY + "\n    private fun openDownloadConnection"
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit("[step374] could not locate downloadResumable function")
    path.write_text(updated, encoding="utf-8")
    print("Step 374 asset download retry repair: PASS")


if __name__ == "__main__":
    main()
