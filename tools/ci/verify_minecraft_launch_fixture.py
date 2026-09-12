#!/usr/bin/env python3
"""Step 180: validate a real Minecraft 1.21.1 launch classpath fixture.

Builds on Step 179's real Mojang downloads and verifies that the actual client
JAR contains Minecraft's Java entry point and that every Linux-applicable
library selected for the version can be represented as a concrete classpath
entry. This does not claim a successful game boot; Android/GLFW execution is
validated separately by the APK emulator smoke test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import urllib.request
import zipfile

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
VERSION_ID = "1.21.1"
MAIN_CLASS = "net/minecraft/client/main/Main.class"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_checked(url: str, destination: Path, expected_sha1: str, expected_size: int | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=120) as response, destination.open("wb") as handle:
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            handle.write(chunk)
    if expected_size is not None and destination.stat().st_size != expected_size:
        raise SystemExit(f"Size mismatch for {url}")
    actual = sha1_file(destination)
    if actual != expected_sha1:
        raise SystemExit(f"SHA-1 mismatch for {url}: got {actual}, expected {expected_sha1}")


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
    with tempfile.TemporaryDirectory(prefix="craftdroid-180-") as temp_dir:
        root = Path(temp_dir)
        manifest = fetch_json(MANIFEST_URL)
        entry = next((v for v in manifest.get("versions", []) if v.get("id") == VERSION_ID), None)
        if not isinstance(entry, dict) or not entry.get("url"):
            raise SystemExit(f"Minecraft {VERSION_ID} is missing from Mojang version manifest")
        detail = fetch_json(entry["url"])

        if detail.get("id") != VERSION_ID:
            raise SystemExit("Version detail ID mismatch")
        java_major = detail.get("javaVersion", {}).get("majorVersion")
        if java_major != 21:
            raise SystemExit(f"Expected Java 21, got {java_major}")
        main_class = detail.get("mainClass")
        if main_class != MAIN_CLASS.removesuffix(".class").replace("/", "."):
            raise SystemExit(f"Unexpected mainClass: {main_class}")

        client = (detail.get("downloads") or {}).get("client") or {}
        client_path = root / "versions" / VERSION_ID / f"{VERSION_ID}.jar"
        download_checked(client["url"], client_path, client["sha1"], int(client["size"]))
        with zipfile.ZipFile(client_path) as jar:
            names = set(jar.namelist())
            if MAIN_CLASS not in names:
                raise SystemExit(f"Minecraft client JAR is missing {MAIN_CLASS}")

        classpath = [client_path]
        libraries = 0
        native_archives = 0
        for lib in detail.get("libraries", []):
            if not allowed_on_linux(lib):
                continue
            downloads = lib.get("downloads") or {}
            artifact = downloads.get("artifact")
            if isinstance(artifact, dict) and artifact.get("url") and artifact.get("sha1") and artifact.get("path"):
                destination = root / "libraries" / artifact["path"]
                download_checked(
                    artifact["url"],
                    destination,
                    artifact["sha1"],
                    int(artifact["size"]) if artifact.get("size") is not None else None,
                )
                classpath.append(destination)
                libraries += 1
            classifiers = downloads.get("classifiers") or {}
            natives = lib.get("natives") or {}
            classifier_template = natives.get("linux")
            if classifier_template:
                classifier = classifier_template.replace("${arch}", "64")
                native = classifiers.get(classifier)
                if isinstance(native, dict) and native.get("url") and native.get("sha1") and native.get("path"):
                    destination = root / "libraries" / native["path"]
                    download_checked(
                        native["url"],
                        destination,
                        native["sha1"],
                        int(native["size"]) if native.get("size") is not None else None,
                    )
                    native_archives += 1

        if not classpath:
            raise SystemExit("Launch classpath is empty")
        if libraries == 0:
            raise SystemExit("No Linux-applicable library artifacts were resolved")

        print("Step 180 Minecraft launch fixture: PASS")
        print(f"version={VERSION_ID}")
        print(f"java={java_major}")
        print(f"mainClass={main_class}")
        print(f"clientSha1={sha1_file(client_path)}")
        print(f"classpathEntries={len(classpath)}")
        print(f"libraryArtifacts={libraries}")
        print(f"nativeArchives={native_archives}")


if __name__ == "__main__":
    main()
