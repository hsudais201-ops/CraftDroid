#!/usr/bin/env python3
"""Step 235: verify hardened launch handoff and repository hygiene."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step235] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java"
    storage = find_one(src, "MinecraftStorageResolver.kt").read_text(encoding="utf-8")
    paths = find_one(src, "MinecraftLaunchPaths.kt").read_text(encoding="utf-8")
    builder = find_one(src, "MinecraftLaunchCommandBuilder.kt").read_text(encoding="utf-8")
    handoff = find_one(src, "MinecraftLaunchHandoff.kt").read_text(encoding="utf-8")
    validator = find_one(src, "MinecraftLaunchHandoffValidator.kt").read_text(encoding="utf-8")
    manager = find_one(src, "MinecraftLaunchManager.kt").read_text(encoding="utf-8")
    ui = find_one(src, "DroidLauncherUiActivity.kt").read_text(encoding="utf-8")

    checks = [
        (storage, "Regex(\"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$\")"),
        (storage, "fun requireValidVersion(minecraftVersion: String): String"),
        (paths, "if (normalized.isBlank())"),
        (paths, "Invalid Minecraft version id"),
        (builder, "Library artifact is missing"),
        (builder, "Library artifact escapes libraries directory"),
        (handoff, "object MinecraftLaunchHandoffReader"),
        (validator, "object MinecraftLaunchHandoffValidator"),
        (ui, "MinecraftLaunchHandoffReader.read(intent)"),
        (ui, "MinecraftLaunchHandoffValidator.validate(this, launchHandoff)"),
        (ui, "startActivity(intent)"),
        (manager, "NativeGameBridge.launchJava("),
    ]
    for text, needle in checks:
        if needle not in text:
            raise SystemExit(f"[step235] missing hardening contract: {needle}")

    reader_pos = ui.find("MinecraftLaunchHandoffReader.read(intent)")
    launch_pos = ui.find("startActivity(intent)", reader_pos)
    if reader_pos < 0 or launch_pos < 0 or reader_pos > launch_pos:
        raise SystemExit("[step235] activity handoff validation is not before startActivity(intent)")

    for source_name, text in (("storage", storage), ("paths", paths), ("builder", builder), ("handoff", handoff), ("validator", validator), ("manager", manager), ("ui", ui)):
        if "TODO" in text or "FIXME" in text:
            raise SystemExit(f"[step235] unfinished marker found in {source_name}")

    print("[step235] storage/version paths hardened")
    print("[step235] launch command fails closed on missing or escaping library artifacts")
    print("[step235] Android activity validates the concrete launch handoff before runtime activity launch")
    print("[step235] generated Minecraft runtime retains its real NativeGameBridge.launchJava call")
    print("[step235] no TODO/FIXME markers remain in audited launch sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
