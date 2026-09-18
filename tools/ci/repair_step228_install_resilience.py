#!/usr/bin/env python3
"""Step 228: add cancellable, persisted Minecraft installation progress and robust downloads."""
from pathlib import Path
import re
import sys


RETRY_DOWNLOAD_BODY = r'''    private fun downloadResumable(task: DownloadTask, version: String, onProgress: (Long, Long) -> Unit) {
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
                if (responseCode !in 200..299) throw IOException("Download failed: HTTP $responseCode for ${task.label}")

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
                            if (isCancellationRequested(version)) throw IOException("Installation cancelled")
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
                if (attempt + 1 < 4) Thread.sleep(500L * (attempt + 1))
            } finally {
                connection?.disconnect()
            }
        }
        throw IOException("Download could not be completed for ${task.label} after 4 attempts", lastError)
    }
'''


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step228] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_download_retry(text: str) -> str:
    pattern = re.compile(r"    private fun downloadResumable\(task: DownloadTask, version: String, onProgress: \(Long, Long\) -> Unit\) \{.*?\n    \}\n\n    private fun openDownloadConnection", re.S)
    replacement = RETRY_DOWNLOAD_BODY + "\n    private fun openDownloadConnection"
    updated, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise SystemExit("[step374] downloadResumable anchor missing")
    return updated


def patch_installer(root: Path) -> None:
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    if "import java.util.concurrent.ConcurrentHashMap" not in text:
        marker = "import java.util.concurrent.Executors\n"
        if marker not in text: raise SystemExit("[step228] executor import anchor missing")
        text = text.replace(marker, marker + "import java.util.concurrent.ConcurrentHashMap\n", 1)
    if "private val cancellations = ConcurrentHashMap.newKeySet<String>()" not in text:
        marker = "    private val executor = Executors.newCachedThreadPool()\n"
        if marker not in text: raise SystemExit("[step228] executor declaration anchor missing")
        text = text.replace(marker, marker + "    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n", 1)
    if "fun cancel(context: Context, version: String)" not in text:
        match = re.search(r"^    fun install\(context: Context, version: String[^\n]*\) \{", text, re.MULTILINE)
        if not match: raise SystemExit("[step228] install(context, version) anchor missing")
        helper = '''    fun cancel(context: Context, version: String) {\n        cancellations.add(version)\n        setState(context, version, State.FAILED, "Installation cancelled")\n    }\n\n    fun isCancellationRequested(version: String): Boolean =\n        cancellations.contains(version)\n\n'''
        text = text[:match.start()] + helper + text[match.start():]
    if "cancellations.remove(version)\n        executor.execute" not in text:
        marker = "        executor.execute {\n            try {"
        if marker not in text: raise SystemExit("[step228] install executor anchor missing")
        text = text.replace(marker, "        cancellations.remove(version)\n        executor.execute {\n            try {", 1)

    text = patch_download_retry(text)

    if "cancellations.remove(version)\n                listener?.onComplete(version)" not in text:
        marker = "                setState(context, version, State.INSTALLED, null)\n                listener?.onComplete(version)"
        if marker not in text: raise SystemExit("[step228] install completion anchor missing")
        text = text.replace(marker, "                setState(context, version, State.INSTALLED, null)\n                cancellations.remove(version)\n                listener?.onComplete(version)", 1)
    if "private fun progressKey(version: String)" not in text:
        pos = text.rfind("\n}")
        if pos < 0: raise SystemExit("[step228] object closing brace not found")
        helper = '''\n    fun savedProgress(context: Context, version: String): Progress {\n        val p = prefs(context)\n        return Progress(version, p.getLong(progressKey(version), 0L), p.getLong(totalKey(version), 0L), p.getString(stageKey(version), "Ready") ?: "Ready", state(context, version))\n    }\n\n    private fun progressKey(version: String) = "mc_install_${version}_downloaded"\n    private fun totalKey(version: String) = "mc_install_${version}_total"\n    private fun stageKey(version: String) = "mc_install_${version}_stage"\n'''
        text = text[:pos] + helper + text[pos:]
    path.write_text(text, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    patch_installer(root)
    text = path.read_text(encoding="utf-8")
    for needle in ("fun cancel(context: Context, version: String)", "isCancellationRequested", "savedProgress(context: Context, version: String)", "private val cancellations", "Download could not be completed for ${task.label} after 4 attempts"):
        if needle not in text: raise SystemExit(f"[step374] missing resilience/retry contract: {needle}")
    print("[step228] installer cancellation contract installed")
    print("[step228] persisted installation progress contract installed")
    print("[step374] transient-empty/short Minecraft download retry contract installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
