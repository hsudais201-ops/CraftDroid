#!/usr/bin/env python3
"""Step 329: restore compile-critical installer/UI contracts after all late generators."""
from pathlib import Path
import sys


def one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step329] expected exactly one {name}, found {len(hits)}")
    return hits[0]


def add_once(text: str, anchor: str, block: str, label: str) -> str:
    if block.strip() in text:
        return text
    pos = text.find(anchor)
    if pos < 0:
        raise SystemExit(f"[step329] anchor missing for {label}: {anchor}")
    return text[:pos] + block + text[pos:]


def patch_installer(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = path.read_text(encoding="utf-8")

    if "fun isLaunchReady(context: Context, version: String): Boolean" not in s:
        anchor = "    fun lastError(context: Context, version: String): String? ="
        block = '''    /** Full pre-launch readiness gate for the selected vanilla installation. */
    fun isLaunchReady(context: Context, version: String): Boolean {
        if (!isInstalled(context, version)) return false
        val root = versionRoot(context, version)
        val client = File(root, "$version.jar")
        val metadata = File(root, "$version.json")
        return client.isFile && client.length() > 0L && metadata.isFile && metadata.length() > 0L
    }

'''
        s = add_once(s, anchor, block, "isLaunchReady")

    if "fun savedProgress(context: Context, version: String): Progress" not in s:
        anchor = "    fun install(context: Context, version: String, listener: Listener? = null) {"
        block = '''    /** Returns the last persisted download progress for UI restoration. */
    fun savedProgress(context: Context, version: String): Progress {
        val p = prefs(context)
        return Progress(
            version = version,
            downloaded = p.getLong(progressKey(version), 0L),
            total = p.getLong(totalKey(version), 0L),
            stage = p.getString(stageKey(version), "Ready") ?: "Ready",
            state = state(context, version)
        )
    }

'''
        s = add_once(s, anchor, block, "savedProgress")

    if "private val cancellations = ConcurrentHashMap.newKeySet<String>()" not in s:
        if "import java.util.concurrent.ConcurrentHashMap" not in s:
            s = s.replace(
                "import java.util.concurrent.Executors\n",
                "import java.util.concurrent.Executors\nimport java.util.concurrent.ConcurrentHashMap\n",
                1,
            )
        s = s.replace(
            "    private val executor = Executors.newCachedThreadPool()\n",
            "    private val executor = Executors.newCachedThreadPool()\n    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n    @Volatile private var progressContext: Context? = null\n",
            1,
        )
    elif "@Volatile private var progressContext: Context? = null" not in s:
        s = s.replace(
            "    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n",
            "    private val cancellations = ConcurrentHashMap.newKeySet<String>()\n    @Volatile private var progressContext: Context? = null\n",
            1,
        )

    if "fun cancel(context: Context, version: String)" not in s:
        anchor = "    fun install(context: Context, version: String, listener: Listener? = null) {"
        block = '''    fun cancel(context: Context, version: String) {
        cancellations.add(version)
        setState(context, version, State.FAILED, "Installation cancelled")
    }

    fun isCancellationRequested(version: String): Boolean = cancellations.contains(version)

'''
        s = add_once(s, anchor, block, "cancel")

    if "progressContext = context.applicationContext" not in s:
        marker = "        if (isInstalled(context, version)) {\n            listener?.onComplete(version)\n            return\n        }\n"
        if marker not in s:
            raise SystemExit("[step329] install preflight anchor missing")
        s = s.replace(marker, marker + "        progressContext = context.applicationContext\n        cancellations.remove(version)\n", 1)
    else:
        s = s.replace("        cancellations.remove(version)\n        executor.execute", "        cancellations.remove(version)\n        progressContext = context.applicationContext\n        executor.execute", 1)

    if "if (isCancellationRequested(version))" not in s:
        marker = "                    while (true) {\n                        val count = input.read(buffer)"
        if marker not in s:
            raise SystemExit("[step329] resumable download loop anchor missing")
        s = s.replace(
            marker,
            "                    while (true) {\n                        if (isCancellationRequested(version)) throw IOException(\"Installation cancelled\")\n                        val count = input.read(buffer)",
            1,
        )

    report_start = "    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {"
    if report_start not in s:
        raise SystemExit("[step329] report function missing")
    brace = s.find("{", s.find(report_start))
    if brace < 0:
        raise SystemExit("[step329] report opening brace missing")
    depth = 0
    end = -1
    in_string = False
    escaped = False
    for i in range(brace, len(s)):
        ch = s[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
    if end < 0:
        raise SystemExit("[step329] report body unterminated")
    report_body = '''    private fun report(listener: Listener?, version: String, downloaded: Long, total: Long, stage: String) {
        progressContext?.let { context ->
            prefs(context).edit()
                .putLong(progressKey(version), downloaded.coerceAtLeast(0L))
                .putLong(totalKey(version), total.coerceAtLeast(0L))
                .putString(stageKey(version), stage)
                .apply()
        }
        listener?.onProgress(Progress(version, downloaded, total, stage, State.DOWNLOADING))
    }'''
    s = s[:s.find(report_start)] + report_body + s[end:]

    if "private fun progressKey(version: String)" not in s:
        pos = s.rfind("\n}")
        if pos < 0:
            raise SystemExit("[step329] installer closing brace missing")
        block = '''
    private fun progressKey(version: String) = "mc_install_${version}_downloaded"
    private fun totalKey(version: String) = "mc_install_${version}_total"
    private fun stageKey(version: String) = "mc_install_${version}_stage"
'''
        s = s[:pos] + block + s[pos:]

    path.write_text(s, encoding="utf-8")


def patch_ui(root: Path) -> None:
    path = one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    s = path.read_text(encoding="utf-8")

    s = s.replace("setTextColor(this@DroidLauncherUiActivity.text)", "setTextColor(primaryText)")
    s = s.replace("setTextColor(text)", "setTextColor(primaryText)")

    if "private fun saveMinecraftVersion(version: String)" not in s:
        anchor = "    private fun rendererPage() {"
        block = '''    private fun saveMinecraftVersion(version: String) {
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .edit().putString("selected_minecraft_version", version.trim()).apply()
    }

'''
        s = add_once(s, anchor, block, "saveMinecraftVersion")

    if "private fun selectedMinecraftVersion(): String" not in s:
        anchor = "    private fun rendererPage() {"
        block = '''    private fun selectedMinecraftVersion(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_version", "1.21.11")?.trim().orEmpty().ifBlank { "1.21.11" }

'''
        s = add_once(s, anchor, block, "selectedMinecraftVersion")

    if "private fun selectedMinecraftProfile(): String" not in s:
        anchor = "    private fun rendererPage() {"
        block = '''    private fun selectedMinecraftProfile(): String =
        getSharedPreferences("droid_launcher", MODE_PRIVATE)
            .getString("selected_minecraft_profile", "Default")?.trim().orEmpty().ifBlank { "Default" }

'''
        s = add_once(s, anchor, block, "selectedMinecraftProfile")

    path.write_text(s, encoding="utf-8")


def patch_tuner(root: Path) -> None:
    path = one(root / "app/src/main/java", "MinecraftPerformanceTuner.kt")
    s = path.read_text(encoding="utf-8")
    old = '''            val (renderDistance, simulationDistance, graphics, particles, clouds, entityShadows) = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> listOf(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> listOf(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> listOf(14, 8, "fancy", "all", "true", "true")
            }
'''
    new = '''            data class TierSettings(
                val renderDistance: Int,
                val simulationDistance: Int,
                val graphics: String,
                val particles: String,
                val clouds: String,
                val entityShadows: String
            )
            val settings = when (profile.tier) {
                PerformanceProfile.Tier.LOW -> TierSettings(6, 4, "fast", "minimal", "false", "false")
                PerformanceProfile.Tier.BALANCED -> TierSettings(10, 6, "fast", "decreased", "false", "true")
                PerformanceProfile.Tier.HIGH -> TierSettings(14, 8, "fancy", "all", "true", "true")
            }
            val renderDistance = settings.renderDistance
            val simulationDistance = settings.simulationDistance
            val graphics = settings.graphics
            val particles = settings.particles
            val clouds = settings.clouds
            val entityShadows = settings.entityShadows
'''
    if old in s:
        s = s.replace(old, new, 1)
    path.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    patch_installer(root)
    patch_ui(root)
    patch_tuner(root)
    print("[step329] post-generation compile contracts restored")
    print("[step329] installer retains launch-readiness, persisted progress and cancellation APIs")
    print("[step329] UI version-selection helpers and text-color references are compile-safe")
    print("[step329] performance tier destructuring replaced with a typed settings record")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
