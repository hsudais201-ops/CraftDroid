#!/usr/bin/env python3
"""Step 224: validate the selected Minecraft installation before launch."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    manager = src / "MinecraftVersionInstallManager.kt"
    ui = src / "DroidLauncherUiActivity.kt"
    if not manager.exists():
        raise SystemExit(f"[step224] missing installer: {manager}")
    if not ui.exists():
        raise SystemExit(f"[step224] missing UI: {ui}")

    m = manager.read_text(encoding="utf-8")
    if "fun isLaunchReady(context: Context, version: String): Boolean" not in m:
        anchor = '    fun isInstalled(context: Context, version: String): Boolean {'
        helper = '''    /** Returns true only when the selected version has the core metadata,
     * client JAR, declared Maven artifacts, and asset index required for launch. */
    fun isLaunchReady(context: Context, version: String): Boolean {
        if (!isInstalled(context, version)) return false
        return try {
            val root = minecraftRoot(context)
            val versionDir = versionRoot(context, version)
            val metadataFile = File(versionDir, "$version.json")
            val metadata = JSONObject(metadataFile.readText(Charsets.UTF_8))

            val downloads = metadata.optJSONObject("downloads") ?: return false
            val client = downloads.optJSONObject("client") ?: return false
            if (!isArtifactHealthy(File(versionDir, "$version.jar"), client.optString("sha1"), client.optLong("size", -1L))) {
                return false
            }

            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    val ld = library.optJSONObject("downloads") ?: continue
                    val artifact = ld.optJSONObject("artifact")
                    if (artifact != null) {
                        val path = artifact.optString("path")
                        if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), artifact.optString("sha1"), artifact.optLong("size", -1L))) {
                            return false
                        }
                    }
                    val classifiers = ld.optJSONObject("classifiers")
                    if (classifiers != null) {
                        val keys = classifiers.keys()
                        while (keys.hasNext()) {
                            val entry = classifiers.optJSONObject(keys.next()) ?: continue
                            val path = entry.optString("path")
                            if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), entry.optString("sha1"), entry.optLong("size", -1L))) {
                                return false
                            }
                        }
                    }
                }
            }

            val index = metadata.optJSONObject("assetIndex")
            if (index != null) {
                val id = index.optString("id")
                val sha1 = index.optString("sha1")
                if (id.isBlank() || !isArtifactHealthy(File(root, "assets/indexes/$id.json"), sha1, index.optLong("size", -1L))) {
                    return false
                }
            }
            true
        } catch (_: Throwable) {
            false
        }
    }

'''
        if anchor not in m:
            raise SystemExit('[step224] isInstalled anchor not found')
        m = m.replace(anchor, helper + anchor, 1)
        manager.write_text(m, encoding="utf-8")

    s = ui.read_text(encoding="utf-8")
    old = '''    private fun launchSelectedMinecraft() {
        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
'''
    new = '''    private fun launchSelectedMinecraft() {
        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
        if (!MinecraftVersionInstallManager.isLaunchReady(this, version)) {
            Toast.makeText(this, "Minecraft $version is not ready. Install or repair it first.", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
'''
    if 'isLaunchReady(this, version)' not in s:
        if old not in s:
            raise SystemExit('[step224] launchSelectedMinecraft anchor not found')
        s = s.replace(old, new, 1)

    old_game = '        val installed = MinecraftVersionInstallManager.isInstalled(this, version)\n'
    new_game = '        val installed = MinecraftVersionInstallManager.isLaunchReady(this, version)\n'
    s = s.replace(old_game, new_game, 1)

    s = s.replace('grep -F \'MinecraftVersionInstallManager.isInstalled\' "$UI" >/dev/null', 'grep -F \'MinecraftVersionInstallManager.isLaunchReady\' "$UI" >/dev/null')
    ui.write_text(s, encoding="utf-8")
    print('[step224] launch preflight added')
    print('[step224] core client, libraries and asset-index validation now gates Play')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
