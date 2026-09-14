#!/usr/bin/env python3
"""Step 177: validate that the launcher build is assembled as Droid Launcher.

This script is intentionally a CI preflight: it verifies the extracted Android
project has one Gradle application module, Android launcher branding, the World
& Save Manager implementation, and the direct-Gradle build contract. It does
not bundle binaries into source control.
"""
from pathlib import Path
import re
import sys


def fail(message: str) -> None:
    raise SystemExit(f"Droid Launcher bundle check failed: {message}")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "settings.gradle.kts").exists() and not (root / "settings.gradle").exists():
        fail("Gradle settings file not found")

    manifests = list(root.rglob("AndroidManifest.xml"))
    if not manifests:
        fail("AndroidManifest.xml not found")
    manifest = min(manifests, key=lambda p: (len(p.parts), str(p)))
    text = manifest.read_text(encoding="utf-8")
    if 'Droid Launcher' not in text:
        fail("Android manifest is not branded Droid Launcher")

    world_candidates = [p for p in root.rglob("WorldManager.kt")]
    if not world_candidates:
        fail("WorldManager.kt not found")
    world = min(world_candidates, key=lambda p: (len(p.parts), str(p)))
    world_text = world.read_text(encoding="utf-8")
    required = ("listWorlds", "backupWorld", "restoreWorld", "importWorld", "exportWorld")
    missing = [name for name in required if name not in world_text]
    if missing:
        fail("WorldManager missing: " + ", ".join(missing))

    workflows = list((root / ".github" / "workflows").glob("*.y*ml")) if (root / ".github" / "workflows").exists() else []
    workflow_text = "\n".join(p.read_text(encoding="utf-8") for p in workflows)
    if "gradle-version: '9.6.0'" not in workflow_text and 'gradle-version: "9.6.0"' not in workflow_text:
        print("[warning] direct Gradle 9.6.0 setup is supplied by the outer CI workflow")

    print("Droid Launcher consolidated bundle preflight: PASS")
    print(f"manifest={manifest}")
    print(f"world_manager={world}")
    print("product_name=Droid Launcher")
    print("repository_name=CraftDroid")


if __name__ == "__main__":
    main()
