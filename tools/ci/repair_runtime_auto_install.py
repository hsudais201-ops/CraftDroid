#!/usr/bin/env python3
"""Step 176: enforce automatic Java/renderer preparation in the launcher.

The source archive remains unchanged. CI applies this guard after extraction.
It verifies that game start resolves Java and the Android-native renderer before
starting the embedded JVM, and keeps Java 17/21/25 first-class while retaining
legacy 8/16 compatibility.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {filename}, found {len(matches)}")
    return matches[0]


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    src = root / "app" / "src" / "main" / "java"
    if not src.is_dir():
        raise SystemExit(f"Android source directory not found: {src}")

    manager = find_one(src, "MinecraftLaunchManager.kt")
    text = manager.read_text(encoding="utf-8")

    if "javaManager.ensureRuntime(requiredJava)" not in text:
        raise SystemExit("Game start does not automatically resolve JavaRuntimeManager.ensureRuntime(requiredJava)")
    if "rendererManager.ensureNativeStack(requestedNativeLwjgl)" not in text:
        raise SystemExit("Game start does not automatically resolve RendererManager.ensureNativeStack(requestedNativeLwjgl)")

    # Keep modern Java 17/21/25 first-class. Legacy 8/16 remains supported.
    gate = re.compile(r"requiredJava\s*!\s*in\s*setOf\(([^)]*)\)")
    match = gate.search(text)
    if match:
        values = {v.strip() for v in match.group(1).split(",") if v.strip()}
        wanted = {"8", "16", "17", "21", "25"}
        if not wanted.issubset(values):
            merged = ", ".join(sorted(values | wanted, key=int))
            text = text[:match.start(1)] + merged + text[match.end(1):]
            manager.write_text(text, encoding="utf-8")
            print("[repair] ensured Java 8/16/17/21/25 compatibility gate")
        else:
            print("[repair] Java 8/16/17/21/25 compatibility gate already present")
    else:
        if not all(f'"{v}"' in text for v in ("17", "21", "25")):
            raise SystemExit("Could not verify Java 17/21/25 support in MinecraftLaunchManager.kt")
        print("[repair] Java 17/21/25 support detected")

    marker = "                val nativeStack = rendererManager.ensureNativeStack(requestedNativeLwjgl) { status ->\n"
    logline = '                LauncherLogger.info("Renderer/native stack: automatic install/repair enabled")\n'
    if logline not in text:
        if marker not in text:
            raise SystemExit("Renderer automatic-install marker not found")
        text = text.replace(marker, logline + marker, 1)
        manager.write_text(text, encoding="utf-8")
        print("[repair] added renderer automatic-install startup log")

    runtime_manager = find_one(src, "JavaRuntimeManager.kt")
    runtime_text = runtime_manager.read_text(encoding="utf-8")
    if "ensureRuntime" not in runtime_text:
        raise SystemExit("JavaRuntimeManager.kt does not expose ensureRuntime()")
    if "Build.SUPPORTED_ABIS" not in runtime_text:
        raise SystemExit("JavaRuntimeManager.kt does not expose Android ABI selection")
    if "private fun verifySha256" not in runtime_text:
        raise SystemExit("JavaRuntimeManager.kt does not expose SHA-256 verification")
    if '"%02x".format(it)' in runtime_text:
        raise SystemExit("JavaRuntimeManager.kt still formats signed SHA-256 bytes directly")
    if "byte.toInt() and 0xff" not in runtime_text:
        raise SystemExit("JavaRuntimeManager.kt SHA-256 byte normalization is missing")
    for major in ("8", "17", "21", "25"):
        if major not in runtime_text:
            raise SystemExit(f"JavaRuntimeManager.kt missing Java {major} runtime contract")
    print("[repair] Android JRE manager ABI/SHA-256/runtime contracts verified")

    renderer_manager = find_one(src, "RendererManager.kt")
    if "ensureNativeStack" not in renderer_manager.read_text(encoding="utf-8"):
        raise SystemExit("RendererManager.kt does not expose ensureNativeStack()")

    print("[repair] Step 176 automatic Java/renderer install contract complete")


if __name__ == "__main__":
    main()
