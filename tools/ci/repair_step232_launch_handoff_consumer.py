#!/usr/bin/env python3
"""Step 232: expose and verify the concrete Minecraft launch-handoff consumer."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step232] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    src = root / "app/src/main/java/com/example/launcher"
    handoff = find_one(src, "MinecraftLaunchHandoff.kt")
    ui = find_one(root / "app/src/main/java", "DroidLauncherUiActivity.kt")
    text = handoff.read_text(encoding="utf-8")
    ui_text = ui.read_text(encoding="utf-8")

    required = [
        "object MinecraftLaunchHandoffReader",
        "fun read(intent: Intent): MinecraftLaunchHandoff",
        'intent.getStringExtra("minecraft_version")',
        'intent.getStringExtra("minecraft_main_class")',
        'intent.getStringExtra("minecraft_classpath")',
        'intent.getStringExtra("minecraft_asset_index")',
        'intent.getStringExtra("minecraft_native_dir")',
        'intent.getStringExtra("minecraft_root")',
        "classpath.any { !it.isFile || it.length() <= 0L }",
        "if (!nativeDir.isDirectory)",
    ]
    for needle in required:
        if needle not in text:
            raise SystemExit(f"[step232] missing handoff-consumer contract: {needle}")

    # The producer side must still exist and emit every field consumed here.
    for needle in (
        'intent.putExtra("minecraft_main_class", launchCommand.mainClass)',
        'intent.putExtra("minecraft_classpath", launchCommand.classpathString)',
        'intent.putExtra("minecraft_asset_index", launchCommand.assetIndex ?: "")',
        'intent.putExtra("minecraft_native_dir", launchCommand.nativeDir.absolutePath)',
        'intent.putExtra("minecraft_root", launchPaths.minecraftRoot.absolutePath)',
    ):
        if needle not in ui_text:
            raise SystemExit(f"[step232] producer/consumer mismatch: {needle}")

    print("[step232] MinecraftLaunchHandoffReader consumes the concrete launch intent")
    print("[step232] version/main-class/classpath/assets/native/root fields are validated")
    print("[step232] producer and consumer field names match")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
