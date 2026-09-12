#!/usr/bin/env python3
"""Step 179: exercise a real Minecraft 1.21.1 installation fixture.

Downloads the actual Mojang 1.21.1 version metadata, client JAR, asset index,
and Linux-applicable library artifacts. Every downloaded artifact is checked
against Mojang's SHA-1 metadata and the client JAR is also checked as a valid
ZIP. This verifies the external inputs required by CraftDroid's installer,
without pretending to launch the game in CI.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import urllib.request
import zipfile

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
VERSION_ID = "1.21.1"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_checked(url: str, destination: Path, expected_sha1: str, expected_size: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    actual_size = destination.stat().st_size
    if expected_size is not None and actual_size != expected_size:
        raise SystemExit(f"Size mismatch for {url}: got {actual_size}, expected {expected_size}")
    actual_sha1 = sha1_file(destination)
    if actual_sha1 != expected_sha1:
        raise SystemExit(f"SHA-1 mismatch for {url}: got {actual_sha1}, expected {expected_sha1}")


def allowed_on_linux(lib: dict) -> bool:
    rules = lib.get("rules")
    if not rules:
        return True
    allowed = False
    for rule in rules:
        os_rule = rule.get("os") or {}
        name = str(os_rule.get("name", "")).lower()
        if name not in ("", "linux", "android"):
            continue
        arch = str(os_rule.get("arch", "")).lower()
        if arch and arch not in ("x86", "x86_64", "amd64", "aarch64", "arm64", "arm", "arm32", "armeabi-v7a"):
            continue
        allowed = str(rule.get("action", "")).lower() == "allow"
    return allowed


def main() -> None:
    out = Path(os.environ.get("CRAFTDROID_FIXTURE_DIR", "")).resolve() if os.environ.get("CRAFTDROID_FIXTURE_DIR") else None
    with tempfile.TemporaryDirectory(prefix="craftdroid-179-") as temp_dir:
        root = out or Path(temp_dir)
        manifest = fetch_json(MANIFEST_URL)
        entry = next((v for v in manifest.get("versions", []) if v.get("id") == VERSION_ID), None)
        if not isinstance(entry, dict) or not entry.get("url"):
            raise SystemExit(f"Minecraft {VERSION_ID} is missing from Mojang version manifest")
        detail = fetch_json(entry["url"])
        if detail.get("id") != VERSION_ID:
            raise SystemExit("Minecraft version detail ID mismatch")

        java_major = detail.get("javaVersion", {}).get("majorVersion")
        if java_major != 21:
            raise SystemExit(f"Minecraft {VERSION_ID} expected Java 21, got {java_major}")

        downloads = detail.get("downloads", {})
        client = downloads.get("client") or {}
        client_path = root / "versions" / VERSION_ID / f"{VERSION_ID}.jar"
        download_checked(client["url"], client_path, client["sha1"], int(client["size"]))
        if not zipfile.is_zipfile(client_path):
            raise SystemExit("Downloaded Minecraft client is not a valid ZIP/JAR")

        asset_index = detail.get("assetIndex") or {}
        asset_path = root / "assets" / "indexes" / f"{asset_index['id']}.json"
        download_checked(asset_index["url"], asset_path, asset_index["sha1"], int(asset_index["size"]))
        asset_index_json = json.loads(asset_path.read_text(encoding="utf-8"))
        objects = asset_index_json.get("objects", {})
        if not isinstance(objects, dict) or not objects:
            raise SystemExit("Minecraft asset index contains no objects")

        library_count = 0
        native_count = 0
        for lib in detail.get("libraries", []):
            if not allowed_on_linux(lib):
                continue
            artifact = (lib.get("downloads") or {}).get("artifact")
            if isinstance(artifact, dict) and artifact.get("url") and artifact.get("sha1") and artifact.get("path"):
                download_checked(
                    artifact["url"],
                    root / "libraries" / artifact["path"],
                    artifact["sha1"],
                    int(artifact["size"]) if artifact.get("size") is not None else None,
                )
                library_count += 1
            classifiers = (lib.get("downloads") or {}).get("classifiers") or {}
            natives = lib.get("natives") or {}
            linux_classifier = natives.get("linux")
            if linux_classifier:
                classifier = linux_classifier.replace("${arch}", "64")
                native = classifiers.get(classifier)
                if isinstance(native, dict) and native.get("url") and native.get("sha1") and native.get("path"):
                    download_checked(
                        native["url"],
                        root / "libraries" / native["path"],
                        native["sha1"],
                        int(native["size"]) if native.get("size") is not None else None,
                    )
                    native_count += 1

        print("Step 179 Minecraft install fixture: PASS")
        print(f"version={VERSION_ID}")
        print(f"java={java_major}")
        print(f"clientSha1={sha1_file(client_path)}")
        print(f"assetIndex={asset_index['id']} objects={len(objects)}")
        print(f"librariesDownloaded={library_count}")
        print(f"nativeArtifactsDownloaded={native_count}")
        print(f"fixtureRoot={root}")


if __name__ == "__main__":
    main()
