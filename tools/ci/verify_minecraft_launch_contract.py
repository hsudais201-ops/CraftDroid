#!/usr/bin/env python3
"""Step 177: verify the real Minecraft launch preparation contract.

This does not pretend to boot Minecraft without game assets/account data. It
statically verifies that the production launch path prepares Java and the
native renderer before the embedded JVM launch, validates the resolved
classpath, and routes launch failures through recovery diagnostics.
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
    require(text, r"LaunchClasspathResolver\.resolve\(", "Minecraft classpath resolution")
    require(text, r"resolvedClasspath\.valid", "classpath validity gate")

    java_pos = text.find("javaManager.ensureRuntime(requiredJava)")
    renderer_pos = text.find("rendererManager.ensureNativeStack(requestedNativeLwjgl)")
    if java_pos < 0 or renderer_pos < 0:
        raise SystemExit("Unable to locate launch preparation calls")

    # The embedded JVM launch must occur only after Java/native preparation.
    jvm_markers = [
        "JvmLaunch",
        "launchJvm",
        "EmbeddedJvm",
        "startJvm",
        "NativeGameBridge",
    ]
    jvm_positions = [text.find(marker) for marker in jvm_markers if text.find(marker) >= 0]
    if not jvm_positions:
        raise SystemExit("Could not identify the embedded JVM/native launch boundary")
    jvm_pos = min(jvm_positions)
    if java_pos > jvm_pos or renderer_pos > jvm_pos:
        raise SystemExit("Java/renderer preparation occurs after the JVM/native launch boundary")

    require(text, r"try\s*\{|runCatching\s*\{", "launch exception boundary")
    recovery_files = list(src.rglob("LaunchRecoveryPolicy.kt"))
    if len(recovery_files) != 1:
        raise SystemExit(f"Expected exactly one LaunchRecoveryPolicy.kt, found {len(recovery_files)}")

    print("Step 177 Minecraft launch contract: PASS")
    print(f"manager={manager}")
    print("verified=Java runtime, renderer/native stack, classpath validity, JVM launch ordering, recovery boundary")


if __name__ == "__main__":
    main()
