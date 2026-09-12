#!/usr/bin/env python3
"""Verify that the real-Minecraft Android boot workflow is wired to the current harness.

This is intentionally deterministic and only checks repository text/configuration;
it does not claim that Minecraft itself booted on an emulator.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def require(text: str, needle: str, label: str) -> None:
    if needle not in text:
        raise SystemExit(f"MISSING: {label}: {needle}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root)
    workflow = root / ".github/workflows/minecraft-real-boot.yml"
    harness = root / "tools/ci/real_minecraft_boot_step182.sh"
    if not workflow.is_file():
        raise SystemExit(f"Missing workflow: {workflow}")
    if not harness.is_file():
        raise SystemExit(f"Missing harness: {harness}")

    w = workflow.read_text(encoding="utf-8")
    h = harness.read_text(encoding="utf-8")

    # Manual and workflow_run paths must both be available.
    require(w, "workflow_dispatch:", "manual dispatch")
    require(w, "workflow_run:", "build-completion trigger")
    require(w, "actions: read", "artifact read permission")
    require(w, "CraftDroid-debug-apk", "APK artifact name")
    require(w, "test \"$BUILD_STATUS\" = success", "successful build check")
    require(w, "test \"$BUILD_SHA\" = \"$TARGET_SHA\"", "source/APK commit match")
    require(w, "Preflight APK for x86_64 Android emulator", "APK preflight")
    require(w, "lib/x86_64/libcraftdroidbridge.so", "x86_64 native bridge check")
    require(w, "real_minecraft_boot_step182.sh \"$APK\"", "production real-boot harness")

    # The harness must isolate the Play event and preserve post-Play diagnostics.
    require(h, '"$ADB" logcat -c', "pre-Play log boundary")
    require(h, "post-play-log-boundary.txt", "post-Play boundary record")
    require(h, "crash-logcat-60s.txt", "crash-buffer capture")
    require(h, "processes.txt", "process snapshot")
    require(h, "logcat-60s.txt", "60-second log capture")
    require(h, "ui-after-play.xml", "post-Play UI capture")
    require(h, "No post-Play Minecraft JVM launch marker was observed", "strict launch result")

    print("PASS: real Minecraft Android boot workflow/harness contract is wired correctly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
