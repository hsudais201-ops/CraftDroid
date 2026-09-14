#!/usr/bin/env python3
"""Step 230: make launch preflight match the actual rule-aware installer."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step230] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    installer = find_one(src, "MinecraftVersionInstallManager.kt")
    text = installer.read_text(encoding="utf-8")

    start = text.find("    fun isLaunchReady(context: Context, version: String): Boolean {")
    if start < 0:
        raise SystemExit("[step230] isLaunchReady() not found")
    end = text.find("\n    fun lastError", start)
    if end < 0:
        end = text.find("\n    fun install", start)
    if end < 0:
        raise SystemExit("[step230] could not locate end of isLaunchReady()")

    replacement = '''    /** Full pre-launch validation matching the installer selection rules. */
    fun isLaunchReady(context: Context, version: String): Boolean {
        if (!isInstalled(context, version)) return false
        return try {
            val root = minecraftRoot(context)
            val versionDir = versionRoot(context, version)
            val metadataFile = File(versionDir, "$version.json")
            val metadata = JSONObject(metadataFile.readText(Charsets.UTF_8))

            val downloads = metadata.optJSONObject("downloads") ?: return false
            val client = downloads.optJSONObject("client") ?: return false
            if (!isArtifactHealthy(File(versionDir, "$version.jar"), client.optString("sha1"), client.optLong("size", -1L))) return false

            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    if (!libraryAllowed(library)) continue
                    val ld = library.optJSONObject("downloads") ?: continue
                    val artifact = ld.optJSONObject("artifact")
                    if (artifact != null) {
                        val path = artifact.optString("path")
                        if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), artifact.optString("sha1"), artifact.optLong("size", -1L))) return false
                    }
                    val classifier = preferredNativeClassifier(library)
                    if (!classifier.isNullOrBlank()) {
                        val entry = ld.optJSONObject("classifiers")?.optJSONObject(classifier)
                        if (entry != null) {
                            val path = entry.optString("path")
                            if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), entry.optString("sha1"), entry.optLong("size", -1L))) return false
                        }
                    }
                }
            }

            val index = metadata.optJSONObject("assetIndex")
            if (index != null) {
                val id = index.optString("id")
                val sha1 = index.optString("sha1")
                val indexFile = File(root, "assets/indexes/$id.json")
                if (id.isBlank() || !isArtifactHealthy(indexFile, sha1, index.optLong("size", -1L))) return false
                val objects = JSONObject(indexFile.readText(Charsets.UTF_8)).optJSONObject("objects")
                if (objects != null) {
                    val keys = objects.keys()
                    while (keys.hasNext()) {
                        val obj = objects.optJSONObject(keys.next()) ?: continue
                        val hash = obj.optString("hash")
                        if (hash.length < 3) return false
                        val target = File(root, "assets/objects/${hash.substring(0, 2)}/$hash")
                        if (!isArtifactHealthy(target, hash, obj.optLong("size", -1L))) return false
                    }
                }
            }
            true
        } catch (_: Throwable) {
            false
        }
    }
'''
    text = text[:start] + replacement + text[end:]
    installer.write_text(text, encoding="utf-8")

    check = installer.read_text(encoding="utf-8")
    for needle in (
        "if (!libraryAllowed(library)) continue",
        "val classifier = preferredNativeClassifier(library)",
        'assets/objects/${hash.substring(0, 2)}/$hash',
        "fun isLaunchReady(context: Context, version: String): Boolean",
    ):
        if needle not in check:
            raise SystemExit(f"[step230] missing complete preflight contract: {needle}")
    print("[step230] launch preflight now mirrors rule-aware library selection")
    print("[step230] launch preflight verifies every asset object declared by the asset index")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
