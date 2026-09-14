#!/usr/bin/env python3
"""Step 236: harden Mojang metadata and artifact URL trust checks."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step236] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = path.read_text(encoding="utf-8")

    old = '''        val versionUrl = findVersionUrl(manifest, version)
            ?: throw IOException("Minecraft version $version was not found in the official manifest")

        report(listener, version, 0, 0, "Downloading version metadata")
        val metadata = JSONObject(httpText(versionUrl))
        writeVerifiedText(File(versionDir, "$version.json"), metadata.toString(), null)
'''
    new = '''        val versionEntry = findVersionEntry(manifest, version)
            ?: throw IOException("Minecraft version $version was not found in the official manifest")
        val versionUrl = versionEntry.optString("url")
        requireHttps(versionUrl, "version metadata")

        report(listener, version, 0, 0, "Downloading version metadata")
        val metadataRaw = httpText(versionUrl)
        val expectedMetadataSha1 = versionEntry.optString("sha1")
        val expectedMetadataSize = versionEntry.optLong("size", -1L)
        if (expectedMetadataSha1.isNotBlank() && !sha1Bytes(metadataRaw.toByteArray(Charsets.UTF_8)).equals(expectedMetadataSha1, true)) {
            throw IOException("Version metadata SHA-1 verification failed for $version")
        }
        if (expectedMetadataSize > 0L && metadataRaw.toByteArray(Charsets.UTF_8).size.toLong() != expectedMetadataSize) {
            throw IOException("Version metadata size verification failed for $version")
        }
        val metadata = JSONObject(metadataRaw)
        writeVerifiedText(File(versionDir, "$version.json"), metadataRaw, expectedMetadataSha1.takeIf { it.isNotBlank() })
'''
    if old not in text:
        raise SystemExit("[step236] version metadata block not found")
    text = text.replace(old, new, 1)

    old_helper = '''    private fun findVersionUrl(manifest: JSONObject, version: String): String? {
        val versions = manifest.optJSONArray("versions") ?: return null
        for (i in 0 until versions.length()) {
            val item = versions.optJSONObject(i) ?: continue
            if (item.optString("id") == version) return item.optString("url").takeIf { it.isNotBlank() }
        }
        return null
    }
'''
    new_helper = '''    private fun findVersionEntry(manifest: JSONObject, version: String): JSONObject? {
        val versions = manifest.optJSONArray("versions") ?: return null
        for (i in 0 until versions.length()) {
            val item = versions.optJSONObject(i) ?: continue
            if (item.optString("id") == version) return item
        }
        return null
    }

    private fun requireHttps(rawUrl: String, label: String) {
        val url = try { URL(rawUrl) } catch (_: Throwable) { throw IOException("Invalid URL for $label") }
        if (!url.protocol.equals("https", ignoreCase = true)) throw IOException("Non-HTTPS URL rejected for $label")
    }

    private fun sha1Bytes(bytes: ByteArray): String {
        val digest = MessageDigest.getInstance("SHA-1")
        digest.update(bytes)
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
'''
    if old_helper not in text:
        raise SystemExit("[step236] version manifest helper not found")
    text = text.replace(old_helper, new_helper, 1)

    old_task = '''        val url = obj.optString("url")
        val sha1 = obj.optString("sha1")
'''
    new_task = '''        val url = obj.optString("url")
        requireHttps(url, label)
        val sha1 = obj.optString("sha1")
'''
    if old_task not in text:
        raise SystemExit("[step236] download-task URL block not found")
    text = text.replace(old_task, new_task, 1)

    old_http = '''    private fun httpText(url: String): String {
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
'''
    new_http = '''    private fun httpText(url: String): String {
        requireHttps(url, "HTTP request")
        val connection = (URL(url).openConnection() as HttpURLConnection).apply {
'''
    if old_http not in text:
        raise SystemExit("[step236] httpText anchor not found")
    text = text.replace(old_http, new_http, 1)

    path.write_text(text, encoding="utf-8")
    verify = path.read_text(encoding="utf-8")
    for needle in (
        "findVersionEntry(manifest, version)",
        "expectedMetadataSha1",
        "expectedMetadataSize",
        "requireHttps(versionUrl, \"version metadata\")",
        "private fun requireHttps(rawUrl: String, label: String)",
        "requireHttps(url, label)",
        "requireHttps(url, \"HTTP request\")",
        "private fun sha1Bytes(bytes: ByteArray): String",
    ):
        if needle not in verify:
            raise SystemExit(f"[step236] missing trust contract: {needle}")
    print("[step236] Mojang version metadata is verified against manifest SHA-1/size")
    print("[step236] all installer HTTP URLs are required to use HTTPS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
