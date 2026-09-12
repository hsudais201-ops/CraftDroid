#!/usr/bin/env python3
"""Static runtime preflight for the generated CraftDroid APK.

This does not claim that Minecraft actually boots; it verifies the APK contains
its Java payload and native bridge for every ABI produced by the build.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ABIS = ("arm64-v8a", "armeabi-v7a", "x86", "x86_64")
BRIDGE = "libcraftdroidbridge.so"
ELF_MAGIC = b"\x7fELF"


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
            if len(data) < 4 or data[:4] != ELF_MAGIC:
                raise SystemExit(f"Native bridge is not an ELF shared object: {entry}")
            if len(data) < 64:
                raise SystemExit(f"Native bridge is unexpectedly small: {entry}")

    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    print("APK runtime preflight: PASS")
    print(f"- size: {apk.stat().st_size} bytes")
    print(f"- sha256: {digest}")
    print("- Java payload: classes.dex present")
    print("- Android manifest: present")
    print(f"- native bridge: {BRIDGE} present and ELF for {len(ABIS)} ABIs")

    # readelf on this runner does not reliably accept ELF bytes from stdin.
    # Materialize each APK entry and probe the actual file instead.
    readelf = shutil.which("readelf")
    unzip = shutil.which("unzip")
    if not readelf or not unzip:
        print("- ELF header/type validation: skipped (readelf/unzip unavailable)")
        return

    with tempfile.TemporaryDirectory(prefix="craftdroid-elf-") as tmp:
        tmpdir = Path(tmp)
        for abi in ABIS:
            entry = f"lib/{abi}/{BRIDGE}"
            elf_path = tmpdir / f"{abi}-{BRIDGE}"
            with elf_path.open("wb") as output:
                subprocess.run(
                    [unzip, "-p", str(apk), entry],
                    stdout=output,
                    stderr=subprocess.PIPE,
                    check=True,
                )
            probe = subprocess.run(
                [readelf, "-h", str(elf_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            if "Type:" not in probe.stdout or "DYN" not in probe.stdout:
                raise SystemExit(f"readelf did not identify {abi} bridge as DYN")
    print("- ELF header/type validation: PASS")


if __name__ == "__main__":
    main()
