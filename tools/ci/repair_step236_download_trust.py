#!/usr/bin/env python3
"""Step 236: harden Mojang metadata and artifact URL trust checks.

This repair is intentionally idempotent. Newer installer implementations may
already contain the security contracts; in that case we verify them instead of
trying to replace an obsolete code block.
"""
from pathlib import Path
import re
import subprocess
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step236] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def apply_legacy_migration(text: str) -> str:
    old = '''        val versionUrl = findVersionUrl(manifest, version)\n            ?: throw IOException("Minecraft version $version was not found in the official manifest")\n\n        report(listener, version, 0, 0, "Downloading version metadata")\n        val metadata = JSONObject(httpText(versionUrl))\n        writeVerifiedText(File(versionDir, "$version.json"), metadata.toString(), null)\n'''
    new = '''        val versionEntry = findVersionEntry(manifest, version)\n            ?: throw IOException("Minecraft version $version was not found in the official manifest")\n        val versionUrl = versionEntry.optString("url")\n        requireHttps(versionUrl, "version metadata")\n\n        report(listener, version, 0, 0, "Downloading version metadata")\n        val metadataRaw = httpText(versionUrl)\n        val expectedMetadataSha1 = versionEntry.optString("sha1")\n        val expectedMetadataSize = versionEntry.optLong("size", -1L)\n        val metadataBytes = metadataRaw.toByteArray(Charsets.UTF_8)\n        if (expectedMetadataSha1.isNotBlank() && !sha1Bytes(metadataBytes).equals(expectedMetadataSha1, true)) {\n            throw IOException("Version metadata SHA-1 verification failed for $version")\n        }\n        if (expectedMetadataSize > 0L && metadataBytes.size.toLong() != expectedMetadataSize) {\n            throw IOException("Version metadata size verification failed for $version")\n        }\n        val metadata = JSONObject(metadataRaw)\n        writeVerifiedText(File(versionDir, "$version.json"), metadataRaw, expectedMetadataSha1.takeIf { it.isNotBlank() })\n'''
    if old in text:
        text = text.replace(old, new, 1)

    old_helper = '''    private fun findVersionUrl(manifest: JSONObject, version: String): String? {\n        val versions = manifest.optJSONArray("versions") ?: return null\n        for (i in 0 until versions.length()) {\n            val item = versions.optJSONObject(i) ?: continue\n            if (item.optString("id") == version) return item.optString("url").takeIf { it.isNotBlank() }\n        }\n        return null\n    }\n'''
    new_helper = '''    private fun findVersionEntry(manifest: JSONObject, version: String): JSONObject? {\n        val versions = manifest.optJSONArray("versions") ?: return null\n        for (i in 0 until versions.length()) {\n            val item = versions.optJSONObject(i) ?: continue\n            if (item.optString("id") == version) return item\n        }\n        return null\n    }\n\n    private fun requireHttps(rawUrl: String, label: String) {\n        val url = try { URL(rawUrl) } catch (_: Throwable) { throw IOException("Invalid URL for $label") }\n        if (!url.protocol.equals("https", ignoreCase = true)) throw IOException("Non-HTTPS URL rejected for $label")\n    }\n\n    private fun sha1Bytes(bytes: ByteArray): String {\n        val digest = MessageDigest.getInstance("SHA-1")\n        return digest.digest(bytes).joinToString("") { "%02x".format(it) }\n    }\n'''
    if old_helper in text:
        text = text.replace(old_helper, new_helper, 1)

    old_task = '''        val url = obj.optString("url")\n        val sha1 = obj.optString("sha1")\n'''
    new_task = '''        val url = obj.optString("url")\n        requireHttps(url, label)\n        val sha1 = obj.optString("sha1")\n'''
    if old_task in text and 'requireHttps(url, label)' not in text:
        text = text.replace(old_task, new_task, 1)

    old_http = '''    private fun httpText(url: String): String {\n        val connection = (URL(url).openConnection() as HttpURLConnection).apply {\n'''
    new_http = '''    private fun httpText(url: String): String {\n        requireHttps(url, "HTTP request")\n        val connection = (URL(url).openConnection() as HttpURLConnection).apply {\n'''
    if old_http in text:
        text = text.replace(old_http, new_http, 1)
    return text


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = apply_legacy_migration(path.read_text(encoding="utf-8"))
    path.write_text(text, encoding="utf-8")

    secure_contracts = (
        "findVersionEntry(manifest, version)",
        "expectedMetadataSha1",
        "expectedMetadataSize",
        'requireHttps(versionUrl, "version metadata")',
        "private fun requireHttps(rawUrl: String, label: String)",
        "requireHttps(url, label)",
        'requireHttps(url, "HTTP request")',
        "private fun sha1Bytes(bytes: ByteArray): String",
    )
    verify = path.read_text(encoding="utf-8")
    missing = [needle for needle in secure_contracts if needle not in verify]
    if missing:
        raise SystemExit("[step236] missing trust contracts: " + ", ".join(missing))

    # Reject an old helper that would allow the installer to bypass manifest metadata.
    if "findVersionUrl(manifest, version)" in verify:
        raise SystemExit("[step236] obsolete findVersionUrl call remains")

    step237 = Path(__file__).with_name("repair_step237_generated_compatibility.py")
    subprocess.run([sys.executable, str(step237), str(root)], check=True)
    step257 = Path(__file__).with_name("repair_step257_feature_center_after_ui.py")
    subprocess.run([sys.executable, str(step257), str(root)], check=True)
    step258 = Path(__file__).with_name("repair_step258_predictive_back.py")
    subprocess.run([sys.executable, str(step258), str(root)], check=True)
    print("[step236] trust repair verified/normalized idempotently")
    print("[step236] Mojang metadata SHA-1/size and HTTPS requirements are present")
    print("[step237] generated-source compatibility repair chained successfully")
    print("[step257] Feature Center final repair chained successfully")
    print("[step258] predictive-back migration chained successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
