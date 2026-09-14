#!/usr/bin/env python3
"""Step 224: validate the selected Minecraft installation before launch."""
from pathlib import Path
import sys


def method_end(src: str, start: int) -> int:
    candidates = [src.find('\n    private fun ', start + 1), src.find('\n    companion object', start + 1)]
    candidates = [x for x in candidates if x >= 0]
    if not candidates:
        raise SystemExit('[step224] could not find end of launch method')
    return min(candidates)


def install_preflight(manager: Path) -> None:
    m = manager.read_text(encoding="utf-8")
    if "fun isLaunchReady(context: Context, version: String): Boolean" in m:
        return
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
            if (!isArtifactHealthy(File(versionDir, "$version.jar"), client.optString("sha1"), client.optLong("size", -1L))) return false
            val libraries = metadata.optJSONArray("libraries")
            if (libraries != null) {
                for (i in 0 until libraries.length()) {
                    val library = libraries.optJSONObject(i) ?: continue
                    val ld = library.optJSONObject("downloads") ?: continue
                    val artifact = ld.optJSONObject("artifact")
                    if (artifact != null) {
                        val path = artifact.optString("path")
                        if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), artifact.optString("sha1"), artifact.optLong("size", -1L))) return false
                    }
                    val classifiers = ld.optJSONObject("classifiers")
                    if (classifiers != null) {
                        val keys = classifiers.keys()
                        while (keys.hasNext()) {
                            val entry = classifiers.optJSONObject(keys.next()) ?: continue
                            val path = entry.optString("path")
                            if (path.isNotBlank() && !isArtifactHealthy(File(root, "libraries/$path"), entry.optString("sha1"), entry.optLong("size", -1L))) return false
                        }
                    }
                }
            }
            val index = metadata.optJSONObject("assetIndex")
            if (index != null) {
                val id = index.optString("id")
                if (id.isBlank() || !isArtifactHealthy(File(root, "assets/indexes/$id.json"), index.optString("sha1"), index.optLong("size", -1L))) return false
            }
            true
        } catch (_: Throwable) {
            false
        }
    }

'''
    if anchor not in m:
        raise SystemExit('[step224] isInstalled anchor not found')
    manager.write_text(m.replace(anchor, helper + anchor, 1), encoding="utf-8")


def add_guard_to_method(s: str, signature: str) -> tuple[str, bool]:
    start = s.find(signature)
    if start < 0:
        return s, False
    end = method_end(s, start)
    block = s[start:end]
    if 'MinecraftVersionInstallManager.isLaunchReady(this, version)' in block:
        return s, True
    prefix = ''
    if signature.strip() == 'private fun launchExistingActivityWithServer() {':
        prefix = '''        val version = selectedMinecraftVersion()
        val profile = selectedMinecraftProfile()
'''
    guard = '''        if (!MinecraftVersionInstallManager.isLaunchReady(this, version)) {
            Toast.makeText(this, "Minecraft $version is not ready. Install or repair it first.", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
'''
    if prefix:
        block = block.replace(signature, signature + prefix + guard, 1)
    elif '        val profile = selectedMinecraftProfile()\n' in block:
        block = block.replace('        val profile = selectedMinecraftProfile()\n', '        val profile = selectedMinecraftProfile()\n' + guard, 1)
    elif '        val version = selectedMinecraftVersion()\n' in block:
        block = block.replace('        val version = selectedMinecraftVersion()\n', '        val version = selectedMinecraftVersion()\n' + guard, 1)
    else:
        raise SystemExit(f'[step224] {signature.strip()} lacks version/profile declaration')
    return s[:start] + block + s[end:], True


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    manager = src / "MinecraftVersionInstallManager.kt"
    ui = src / "DroidLauncherUiActivity.kt"
    if not manager.exists(): raise SystemExit(f"[step224] missing installer: {manager}")
    if not ui.exists(): raise SystemExit(f"[step224] missing UI: {ui}")
    install_preflight(manager)
    s = ui.read_text(encoding="utf-8")
    found = False
    for signature in ('    private fun launchSelectedMinecraft() {', '    private fun launchExistingActivityWithServer() {'):
        s, found = add_guard_to_method(s, signature)
        if found: break
    if not found:
        raise SystemExit('[step224] no compatible launch entrypoint found')
    s = s.replace('        val installed = MinecraftVersionInstallManager.isInstalled(this, version)\n', '        val installed = MinecraftVersionInstallManager.isLaunchReady(this, version)\n', 1)
    ui.write_text(s, encoding="utf-8")
    print('[step224] launch preflight added')
    print('[step224] core client, libraries and asset-index validation now gates Play')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
