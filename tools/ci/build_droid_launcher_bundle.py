#!/usr/bin/env python3
from pathlib import Path
import sys


def fail(message: str) -> None:
    raise SystemExit(f"[Droid Launcher preflight] FAIL: {message}")


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    if not root.exists():
        fail(f"project root does not exist: {root}")

    settings = list(root.glob("settings.gradle")) + list(root.glob("settings.gradle.kts"))
    if not settings:
        fail("no settings.gradle(.kts) found")

    manifests = list(root.glob("**/src/main/AndroidManifest.xml"))
    if not manifests:
        fail("no AndroidManifest.xml found")
    if not any("Droid Launcher" in p.read_text(encoding="utf-8", errors="ignore") for p in manifests):
        fail("AndroidManifest.xml does not contain the Droid Launcher application label")

    world_managers = [p for p in root.glob("**/WorldManager.kt") if p.is_file()]
    if world_managers:
        text = world_managers[0].read_text(encoding="utf-8", errors="ignore")
        required = ("listWorlds", "backupWorld", "restoreWorld", "importWorld", "exportWorld")
        missing = [name for name in required if name not in text]
        if missing:
            fail(f"WorldManager.kt is missing expected API: {', '.join(missing)}")
    else:
        print("[Droid Launcher preflight] WARN: WorldManager.kt not present in extracted source yet")

    gradle_files = list(root.glob("**/*.gradle")) + list(root.glob("**/*.gradle.kts"))
    workflow_files = list(Path(__file__).resolve().parents[2].glob(".github/workflows/*.yml"))
    if not gradle_files:
        fail("no Gradle build files found")
    print(f"[Droid Launcher preflight] project={root}")
    print(f"[Droid Launcher preflight] product=Droid Launcher")
    print(f"[Droid Launcher preflight] Gradle files={len(gradle_files)}")
    print(f"[Droid Launcher preflight] repository=CraftDroid")
    print(f"[Droid Launcher preflight] workflows={len(workflow_files)}")
    print("[Droid Launcher preflight] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
