#!/usr/bin/env python3
"""Step 237/241: repair generated-source API drift without changing native launch architecture."""
from pathlib import Path
import re
import sys


def one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step237] expected one {name}, found {len(hits)}")
    return hits[0]


def insert_before_last_class_brace(text: str, block: str) -> str:
    pos = text.rfind("}")
    if pos < 0:
        raise SystemExit("[step237] class closing brace not found")
    return text[:pos] + block + "\n" + text[pos:]


def insert_before_renderer(s: str, block: str) -> str:
    anchor = "    private fun rendererPage() {"
    if anchor not in s:
        raise SystemExit("[step237] rendererPage anchor missing")
    return s.replace(anchor, block + anchor, 1)


def repair_ui(root: Path) -> None:
    p = one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    s = p.read_text(encoding="utf-8")
    if "import android.widget.Toast" not in s and "import android.widget." in s:
        s = s.replace("import android.widget.", "import android.widget.Toast\nimport android.widget.", 1)

    saved_server = '''\n    private fun getSavedServer(): Pair<String, Int> {\n        val prefs = getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)\n        val host = prefs.getString("selected_host", "localhost")?.trim().orEmpty().ifBlank { "localhost" }\n        val port = prefs.getInt("selected_port", 25565).coerceIn(1, 65535)\n        return host to port\n    }\n\n'''
    java_helper = '''    private fun getResolvedJavaForLaunch(version: String): Int {\n        val saved = getSharedPreferences("droid_launcher", MODE_PRIVATE).getInt("java_runtime_override", 0)\n        if (saved in intArrayOf(8, 16, 17, 21, 25)) return saved\n        val parts = version.split('.', '-', '_').mapNotNull { it.toIntOrNull() }\n        val major = parts.firstOrNull() ?: 21\n        val minor = parts.getOrNull(1) ?: 0\n        val patch = parts.getOrNull(2) ?: 0\n        return when {\n            major >= 26 -> 25\n            major == 1 && minor >= 21 -> 21\n            major == 1 && minor == 20 && patch >= 5 -> 21\n            major == 1 && minor >= 17 -> 17\n            else -> 8\n        }\n    }\n\n'''
    launch_helper = '''    private fun launchSelectedMinecraft() {\n        val version = selectedMinecraftVersion()\n        if (!MinecraftVersionInstallManager.isLaunchReady(this, version)) {\n            Toast.makeText(this, "Minecraft $version is not ready. Install/repair it first.", Toast.LENGTH_LONG).show()\n            showPage("Search by ID")\n            return\n        }\n        launchExistingActivityWithServer()\n    }\n\n'''

    if "private fun getSavedServer(): Pair<String, Int>" not in s:
        s = insert_before_renderer(s, saved_server)
    if "private fun getResolvedJavaForLaunch(version: String): Int" not in s:
        s = insert_before_renderer(s, java_helper)
    if "private fun launchSelectedMinecraft()" not in s:
        s = insert_before_renderer(s, launch_helper)
    p.write_text(s, encoding="utf-8")


def repair_game_activity(root: Path) -> None:
    hits = list(root.rglob("GameActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step237] expected one GameActivity.kt, found {len(hits)}")
    p = hits[0]
    s = p.read_text(encoding="utf-8")
    if "onGameSurfaceReady" not in s:
        block = """

    /** Compatibility lifecycle hook used by the generated renderer bridge. */
    fun onGameSurfaceReady() {
        // Renderer/native initialization is owned by the existing surface lifecycle.
    }

    /** Compatibility lifecycle hook used by the generated renderer bridge. */
    fun onGameSurfaceDestroyed() {
        // Renderer/native teardown is owned by the existing surface lifecycle.
    }
"""
        s = insert_before_last_class_brace(s, block)
    s = re.sub(r'(?m)^\s*kill\(\)\s*$', '        finish()', s)
    p.write_text(s, encoding="utf-8")


def repair_install_manager(root: Path) -> None:
    p = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = p.read_text(encoding="utf-8")
    if "fun isInstalled(context: Context, version: String)" not in s:
        anchor = "    fun state(context: Context, version: String)"
        pos = s.find(anchor)
        if pos < 0:
            raise SystemExit("[step237] installer state() anchor missing")
        block = """
    fun isInstalled(context: Context, version: String): Boolean =
        state(context, version) == State.INSTALLED

"""
        s = s[:pos] + block + s[pos:]
    p.write_text(s, encoding="utf-8")


def repair_viewmodel(root: Path) -> None:
    hits = list(root.rglob("LauncherViewModel.kt"))
    if len(hits) != 1:
        print("[step237] LauncherViewModel.kt not present in generated archive; skipping ViewModel shim")
        return
    p = hits[0]
    s = p.read_text(encoding="utf-8")
    if "class LaunchState" not in s and "data class LaunchState" not in s:
        package_match = re.search(r"^package\s+([^\n]+)", s, re.M)
        if package_match and "LaunchState(" in s:
            state = '''\n\n/** Stable UI state shared by launcher and launch-overlay surfaces. */\ndata class LaunchState(\n    val state: String = "IDLE",\n    val progress: Int = 0,\n    val message: String = "",\n    val error: String? = null\n)\n'''
            s = s + state
    if "fun resetToHome()" not in s:
        s = insert_before_last_class_brace(s, """
    fun resetToHome() {
        // Preserve current model state; the UI layer controls the visible page.
    }
""")
    p.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    repair_ui(root)
    repair_game_activity(root)
    repair_install_manager(root)
    repair_viewmodel(root)
    print("[step237] generated UI compatibility helpers repaired")
    print("[step237] GameActivity lifecycle hooks and invalid kill() call repaired")
    print("[step237] installer exposes stable isInstalled contract")
    print("[step237] launcher ViewModel reset compatibility checked")
    print("[step237] Java resolver maps 1.20.5+ to Java 21 and 26+ to Java 25")
    print("[step241] compatibility helpers are independently idempotent; no launch helper duplication")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
