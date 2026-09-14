#!/usr/bin/env python3
"""Step 236: verify installer download trust hardening."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step236] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    installer = find_one(root / "app/src/main/java", "MinecraftVersionInstallManager.kt")
    text = installer.read_text(encoding="utf-8")
    required = (
        "findVersionEntry(manifest, version)",
        "expectedMetadataSha1",
        "expectedMetadataSize",
        "requireHttps(versionUrl, \"version metadata\")",
        "private fun requireHttps(rawUrl: String, label: String)",
        "requireHttps(url, label)",
        "requireHttps(url, \"HTTP request\")",
        "private fun sha1Bytes(bytes: ByteArray): String",
    )
    for needle in required:
        if needle not in text:
            raise SystemExit(f"[step236] missing installer trust contract: {needle}")
    metadata_pos = text.find("expectedMetadataSha1")
    parse_pos = text.find("val metadata = JSONObject(metadataRaw)")
    if metadata_pos < 0 or parse_pos < 0 or metadata_pos > parse_pos:
        raise SystemExit("[step236] metadata integrity verification must precede JSON parsing")
    print("Step 236 download trust verification: PASS")
    print("verified=manifest metadata SHA-1/size, HTTPS-only artifact URLs, HTTPS-only text requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
