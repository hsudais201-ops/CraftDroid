#!/usr/bin/env python3
"""Step 178: validate a real Mojang Minecraft version manifest fixture.

This checks the metadata required to prepare a real client launch without
claiming that the game itself was booted. The fixture is intentionally pinned
to Minecraft 1.21.1 for deterministic CI coverage.
"""
import hashlib
import json
import sys
import urllib.request

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
VERSION_ID = "1.21.1"
EXPECTED_JAVA = 21


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def main() -> None:
    manifest = get_json(MANIFEST_URL)
    versions = manifest.get("versions")
    if not isinstance(versions, list):
        raise SystemExit("Mojang manifest has no versions array")

    entry = next((v for v in versions if v.get("id") == VERSION_ID), None)
    if not isinstance(entry, dict):
        raise SystemExit(f"Minecraft {VERSION_ID} is missing from Mojang version manifest")
    url = entry.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise SystemExit("Version metadata URL is missing or invalid")

    detail = get_json(url)
    if detail.get("id") != VERSION_ID:
        raise SystemExit(f"Version detail ID mismatch: {detail.get('id')!r}")

    for key in ("mainClass", "assetIndex", "downloads", "libraries"):
        if key not in detail:
            raise SystemExit(f"Minecraft {VERSION_ID} metadata missing required field: {key}")

    client = detail["downloads"].get("client")
    if not isinstance(client, dict) or not client.get("url") or not client.get("sha1"):
        raise SystemExit("Minecraft client download metadata is incomplete")

    asset_index = detail["assetIndex"]
    if not isinstance(asset_index, dict) or not asset_index.get("id") or not asset_index.get("url"):
        raise SystemExit("Asset index metadata is incomplete")

    java_version = detail.get("javaVersion", {}).get("majorVersion")
    if java_version != EXPECTED_JAVA:
        raise SystemExit(f"Minecraft {VERSION_ID} requires Java {java_version}, expected {EXPECTED_JAVA}")

    client_url = client["url"]
    req = urllib.request.Request(client_url, headers={"User-Agent": "CraftDroid-CI/1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read(1024 * 1024)
    if not data:
        raise SystemExit("Minecraft client download returned no data")

    print(f"Step 178 Minecraft version fixture: PASS")
    print(f"version={VERSION_ID}")
    print(f"java={java_version}")
    print(f"mainClass={detail['mainClass']}")
    print(f"libraries={len(detail['libraries'])}")
    print(f"assetIndex={asset_index['id']}")
    print(f"clientMetadataSha1={client['sha1']}")
    print(f"clientSampleSha256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
