#!/usr/bin/env python3
"""Static runtime preflight for the generated CraftDroid APK.

This does not claim that Minecraft actually boots; it verifies the APK contains
its Java payload and native bridge for every ABI produced by the build.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ABIS = ("arm64-v8a", "armeabi-v7a", "x86", "x86_64")
BRIDGE = "libcraftdroidbridge.so"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_runtime_preflight.py <apk>")
    apk = Path(sys.argv[1]).resolve()
    if not apk.is_file() or apk.stat().st_size == 0:
        raise SystemExit(f"APK missing or empty: {apk}")

    with zipfile.ZipFile(apk) as zf:
        names = set(zf.namelist())
        required = {"AndroidManifest.xml", "classes.dex"}
        missing = sorted(required - names)
        if missing:
            raise SystemExit(f"Missing required APK entries: {missing}")

        for abi in ABIS:
            entry = f"lib/{abi}/{BRIDGE}"
            if entry not in names:
                raise SystemExit(f"Missing native bridge for {abi}: {entry}")
            data = zf.read(entry)
            if len(data) < 4 or data[:4] != b"\\x7fELF":
                raise SystemExit(f"Native bridge is not an ELF shared object: {entry}")
            if len(data) < 64:
                raise SystemExit(f"Native bridge is unexpectedly small: {entry}")

    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    print(f"APK runtime preflight: PASS")
    print(f"- size: {apk.stat().st_size} bytes")
    print(f"- sha256: {digest}")
    print(f"- Java payload: classes.dex present")
    print(f"- Android manifest: present")
    print(f"- native bridge: {BRIDGE} present and ELF for {len(ABIS)} ABIs")

    # When readelf is available, validate that each bridge is a shared ELF file.
    try:
        for abi in ABIS:
            result = subprocess.run(
                ["unzip", "-p", str(apk), f"lib/{abi}/{BRIDGE}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            probe = subprocess.run(
                ["readelf", "-h", "-"],
                input=result.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
            if b"Type:" not in probe.stdout or b"DYN" not in probe.stdout:
                raise SystemExit(f"readelf did not identify {abi} bridge as DYN")
        print("- ELF header/type validation: PASS")
    except FileNotFoundError:
        print("- readelf validation: skipped (tool unavailable)")


if __name__ == "__main__":
    main()
