#!/usr/bin/env python3
"""Step 235: make the generated Minecraft runtime consume the validated launch handoff.

The real MinecraftLaunchManager is generated from the Step 153 archive. This
repair therefore edits that generated source at CI time and refuses to guess
when the generated launch method does not expose the Android activity intent.
"""
from pathlib import Path
import re
import sys


def find_one(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"[step235] expected exactly one {name}, found {len(matches)}")
    return matches[0]


def method_region(text: str, needle_pos: int) -> tuple[int, int, str]:
    before = text[:needle_pos]
    starts = list(re.finditer(r"(?m)^\s*(?:private\s+|public\s+|internal\s+|protected\s+|override\s+)*(?:suspend\s+)?fun\s+[A-Za-z0-9_]+\s*\([^\n]*", before))
    if not starts:
        raise SystemExit("[step235] could not locate launch method containing NativeGameBridge.launchJava")
    start = starts[-1].start()
    brace = text.find("{", starts[-1].start(), needle_pos)
    if brace < 0:
        raise SystemExit("[step235] launch method opening brace not found")
    depth = 0
    end = len(text)
    for i in range(brace, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    return start, end, text[start:end]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    manager_path = find_one(root / "app/src/main/java", "MinecraftLaunchManager.kt")
    handoff = find_one(root / "app/src/main/java", "MinecraftLaunchHandoff.kt")
    validator = find_one(root / "app/src/main/java", "MinecraftLaunchHandoffValidator.kt")
    text = manager_path.read_text(encoding="utf-8")

    reader_call = "MinecraftLaunchHandoffReader.read(intent)"
    validator_call = "MinecraftLaunchHandoffValidator.validate(this, launchHandoff)"
    if reader_call not in text:
        launch_pos = text.find("NativeGameBridge.launchJava(")
        if launch_pos < 0:
            raise SystemExit("[step235] NativeGameBridge.launchJava( was not found in generated manager")
        start, _end, region = method_region(text, launch_pos)
        if "intent" not in region:
            raise SystemExit("[step235] launch method does not expose the Android activity intent; refusing an unsafe blind patch")
        gate = '''\n        val launchHandoff = MinecraftLaunchHandoffReader.read(intent)\n        val handoffError = MinecraftLaunchHandoffValidator.validate(this, launchHandoff)\n        if (handoffError != null) {\n            throw IllegalStateException("Minecraft launch handoff rejected: $handoffError")\n        }\n'''
        insert_at = launch_pos
        text = text[:insert_at] + gate + text[insert_at:]
        manager_path.write_text(text, encoding="utf-8")

    check = manager_path.read_text(encoding="utf-8")
    for needle in (reader_call, validator_call, "if (handoffError != null)", "NativeGameBridge.launchJava("):
        if needle not in check:
            raise SystemExit(f"[step235] missing runtime handoff gate: {needle}")
    if "object MinecraftLaunchHandoffReader" not in handoff.read_text(encoding="utf-8"):
        raise SystemExit("[step235] launch handoff reader missing")
    if "object MinecraftLaunchHandoffValidator" not in validator.read_text(encoding="utf-8"):
        raise SystemExit("[step235] launch handoff validator missing")

    print("[step235] generated Minecraft runtime now consumes the validated activity handoff")
    print("[step235] patch is fail-closed when the generated manager lacks an activity intent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
