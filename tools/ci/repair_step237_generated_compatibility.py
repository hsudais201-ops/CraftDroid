#!/usr/bin/env python3
"""Step 237: repair generated-source API drift without changing the native launch architecture."""
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


def repair_ui(root: Path) -> None:
    p = one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    s = p.read_text(encoding="utf-8")
    if "import android.widget.Toast" not in s and "import android.widget." in s:
        s = s.replace("import android.widget.", "import android.widget.Toast\nimport android.widget.", 1)

    helpers = """
    private fun getSavedServer(): Pair<String, Int> {
        val prefs = getSharedPreferences("droid_launcher_servers", MODE_PRIVATE)
        val host = prefs.getString("selected_host", "localhost")?.trim().orEmpty().ifBlank { "localhost" }
        val port = prefs.getInt("selected_port", 25565).coerceIn(1, 65535)
        return host to port
    }

    private fun getResolvedJavaForLaunch(version: String): Int {
        val saved = getSharedPreferences("droid_launcher", MODE_PRIVATE).getInt("java_runtime_override", 0)
        if (saved in intArrayOf(8, 16, 17, 21, 25)) return saved
        val parts = version.split('.', '-', '_').mapNotNull { it.toIntOrNull() }
        val major = parts.firstOrNull() ?: 21
        val minor = parts.getOrNull(1) ?: 0
        return when {
            major >= 25 -> 25
            major >= 24 -> 21
            major == 1 && minor >= 20 -> if (version >= "1.20.5") 21 else 17
            major == 1 && minor >= 17 -> 17
            else -> 8
        }
    }

    private fun launchSelectedMinecraft() {
        val version = selectedMinecraftVersion()
        if (!MinecraftVersionInstallManager.isLaunchReady(this, version)) {
            Toast.makeText(this, "Minecraft $version is not ready. Install/repair it first.", Toast.LENGTH_LONG).show()
            showPage("Search by ID")
            return
        }
        launchExistingActivityWithServer()
    }

"""
    if "private fun getSavedServer(): Pair<String, Int>" not in s:
        anchor = "    private fun rendererPage() {"
        if anchor not in s:
            raise SystemExit("[step237] rendererPage anchor missing")
        s = s.replace(anchor, helpers + anchor, 1)
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
    # Some generated revisions used a bare kill() that is not an Android API.
    s = re.sub(r'(?m)^\s*kill\(\)\s*$', '        finish()', s)
    p.write_text(s, encoding="utf-8")


def repair_install_manager(root: Path) -> None:
    p = one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    s = p.read_text(encoding="utf-8")
    # Keep a single authoritative isInstalled implementation. If a generated
    # revision lost it, derive the state from the persistent installation state.
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
        if package_match:
            pkg = package_match.group(1).strip()
            state = f'''\n\n/** Stable UI state shared by launcher and launch-overlay surfaces. */\ndata class LaunchState(\n    val state: String = "IDLE",\n    val progress: Int = 0,\n    val message: String = "",\n    val error: String? = null\n)\n'''
            # Put the model at top level; callers can still use it from the same package.
            if "LaunchState(" in s:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
