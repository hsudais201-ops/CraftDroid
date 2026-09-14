#!/usr/bin/env python3
"""Step 219: connect the persisted Java runtime preference to Minecraft launch."""
from pathlib import Path
import sys

RUNTIME_KEY = "droid.launcher.java.runtime"


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step219] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def patch_ui(root: Path) -> None:
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    s = ui.read_text(encoding="utf-8")
    old = '        getSharedPreferences("droid_launcher", MODE_PRIVATE).edit().putString("selected_java_runtime", value).apply()\n'
    new = old + f'        System.setProperty("{RUNTIME_KEY}", value)\n'
    if f'System.setProperty("{RUNTIME_KEY}", value)' not in s:
        if s.count(old) != 1:
            raise SystemExit("[step219] saveJavaOverride anchor not found uniquely")
        s = s.replace(old, new, 1)

    anchor = '        val selected = getSharedPreferences("droid_launcher", MODE_PRIVATE).getString("selected_java_runtime", "auto") ?: "auto"\n'
    seed = anchor + f'        System.setProperty("{RUNTIME_KEY}", selected)\n'
    if f'System.setProperty("{RUNTIME_KEY}", selected)' not in s:
        if anchor not in s:
            raise SystemExit("[step219] Java-page selected-runtime anchor missing")
        s = s.replace(anchor, seed, 1)
    ui.write_text(s, encoding="utf-8")


def patch_manager(root: Path) -> None:
    manager = find_one(root / "app/src/main/java", "MinecraftLaunchManager.kt")
    s = manager.read_text(encoding="utf-8")
    call = "javaManager.ensureRuntime(requiredJava)"
    if call not in s:
        raise SystemExit("[step219] MinecraftLaunchManager is missing ensureRuntime(requiredJava)")
    replacement = "javaManager.ensureRuntime(resolveLaunchJavaRuntime(requiredJava))"
    if replacement not in s:
        s = s.replace(call, replacement, 1)

    if "private fun resolveLaunchJavaRuntime(requestedJava: String): String" not in s:
        helper = f'''\n    /** Applies an explicit launcher Java override; AUTO preserves the version-derived runtime. */
    private fun resolveLaunchJavaRuntime(requestedJava: String): String {{
        val override = System.getProperty("{RUNTIME_KEY}")?.trim().orEmpty()
        if (override.isEmpty() || override.equals("auto", ignoreCase = true)) return requestedJava
        val normalized = override.removePrefix("Internal-")
        return normalized.takeIf {{ it in setOf("8", "16", "17", "21", "25") }} ?: requestedJava
    }}\n'''
        pos = s.rfind("\n}")
        if pos < 0:
            raise SystemExit("[step219] MinecraftLaunchManager class closing brace not found")
        s = s[:pos] + helper + s[pos:]
    manager.write_text(s, encoding="utf-8")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    if not src.is_dir():
        raise SystemExit(f"[step219] source directory not found: {src}")
    patch_ui(root)
    patch_manager(root)
    manager = find_one(src, "MinecraftLaunchManager.kt").read_text(encoding="utf-8")
    ui = find_one(src, "DroidLauncherUiActivity.kt").read_text(encoding="utf-8")
    checks = [
        (manager, "javaManager.ensureRuntime(resolveLaunchJavaRuntime(requiredJava))"),
        (manager, f'System.getProperty("{RUNTIME_KEY}")'),
        (manager, 'private fun resolveLaunchJavaRuntime(requestedJava: String): String'),
        (ui, f'System.setProperty("{RUNTIME_KEY}", value)'),
        (ui, 'getSharedPreferences("droid_launcher", MODE_PRIVATE)'),
    ]
    for text, needle in checks:
        if needle not in text:
            raise SystemExit(f"[step219] missing contract: {needle}")
    print("[step219] Java preference -> real launch runtime bridge installed")
    print("[step219] AUTO keeps the game-version-derived requiredJava")
    print("[step219] explicit Java 8/16/17/21/25 overrides are applied before ensureRuntime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
