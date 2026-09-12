#!/usr/bin/env python3
"""Step 177: verify the real Minecraft launch preparation contract.

This does not pretend to boot Minecraft without game assets/account data. It
statically verifies that the production launch path prepares Java and the
native renderer before the embedded JVM launch, validates the generated
LaunchCommand with LaunchPreflight, and routes launch failures through the
recovery/error boundary.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {filename}, found {len(matches)}")
    return matches[0]


def require(text: str, pattern: str, label: str) -> None:
    if re.search(pattern, text, re.MULTILINE | re.DOTALL) is None:
        raise SystemExit(f"Minecraft launch contract missing: {label}")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    src = root / "app" / "src" / "main" / "java"
    manager = find_one(src, "MinecraftLaunchManager.kt")
    text = manager.read_text(encoding="utf-8")

    require(text, r"javaManager\.ensureRuntime\(requiredJava\)", "Java runtime preparation")
    require(text, r"rendererManager\.ensureNativeStack\(requestedNativeLwjgl\)", "native renderer preparation")
    require(text, r"LaunchPreflight\.verify\(", "generated launch-command preflight")
    require(text, r"preflight\.valid", "launch-command validity gate")
    require(text, r"NativeGameBridge\.launchJava\(", "embedded JVM launch")

    java_pos = text.find("javaManager.ensureRuntime(requiredJava)")
    renderer_pos = text.find("rendererManager.ensureNativeStack(requestedNativeLwjgl)")
    preflight_pos = text.find("LaunchPreflight.verify(")
    launch_pos = text.find("NativeGameBridge.launchJava(")
    if min(java_pos, renderer_pos, preflight_pos, launch_pos) < 0:
        raise SystemExit("Unable to locate one or more Minecraft launch stages")

    if java_pos > launch_pos:
        raise SystemExit("Java runtime preparation occurs after the JVM launch")
    if renderer_pos > launch_pos:
        raise SystemExit("Native renderer preparation occurs after the JVM launch")
    if preflight_pos > launch_pos:
        raise SystemExit("Launch command preflight occurs after the JVM launch")

    require(text, r"try\s*\{|runCatching\s*\{", "launch exception boundary")
    recovery_files = list(src.rglob("LaunchRecoveryPolicy.kt"))
    if len(recovery_files) != 1:
        raise SystemExit(f"Expected exactly one LaunchRecoveryPolicy.kt, found {len(recovery_files)}")

    print("Step 177 Minecraft launch contract: PASS")
    print(f"manager={manager}")
    print("verified=Java runtime, renderer/native stack, launch-command preflight, embedded JVM launch ordering, recovery boundary")


if __name__ == "__main__":
    main()
