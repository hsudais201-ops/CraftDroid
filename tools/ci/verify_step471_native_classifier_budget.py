#!/usr/bin/env python3
"""Verify that Minecraft installation downloads only the Android/Linux native classifier."""
from pathlib import Path
import sys

def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    p = root / "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt"
    if not p.is_file():
        raise SystemExit(f"[step471] missing installer source: {p}")
    s = p.read_text(encoding="utf-8")
    required = [
        "private fun preferredNativeClassifier(lib: JSONObject): String?",
        "val nativeClassifier = preferredNativeClassifier(lib)",
        'optJSONObject("classifiers")?.optJSONObject(nativeClassifier)',
    ]
    for needle in required:
        if needle not in s:
            raise SystemExit(f"[step471] missing native-classifier contract: {needle}")
    block = s[s.find("val nativeClassifier = preferredNativeClassifier(lib)"):s.find("var totalBytes = 0L")]
    if "classifiers.keys()" in block or "while (keys.hasNext())" in block:
        raise SystemExit("[step471] installer still enumerates every native classifier")
    print("[step471] Android native classifier selection is targeted and bounded: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
