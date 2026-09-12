#!/usr/bin/env python3
"""Deterministically repair native bridge errors exposed by the CI build.

The checked-in CraftDroid source is an archive, so CI applies this repair after
extraction. Repairs are intentionally narrow and fail loudly when source shape
changes.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


def find_file(root: Path, name: str) -> Path:
    matches = list(root.rglob(name))
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one {name}, found {len(matches)}: {matches}")
    return matches[0]


def find_matching_brace(text: str, open_pos: int) -> int:
    depth = 0
    for i in range(open_pos, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    raise SystemExit("Unbalanced braces while locating InputEvent")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: repair_step155_cpp.py <project-root>")

    root = Path(sys.argv[1]).resolve()
    cpp = find_file(root, "craftdroidbridge.cpp")
    text = cpp.read_text(encoding="utf-8")
    original = text

    # Remove stale lifecycle calls found in older archive variants.
    stale_call = re.compile(r"^\s*stopInputPump\(true\);\s*$", re.MULTILINE)
    text, removed = stale_call.subn(
        "        // Step 155: stale stopInputPump(true) call removed; teardown remains active.\n",
        text,
    )
    if removed < 1:
        raise SystemExit("Expected at least one stale stopInputPump(true) call")

    marker = re.search(r"\bstruct\s+InputEvent\s*\{", text)
    if not marker:
        raise SystemExit("InputEvent struct not found")
    open_pos = text.find("{", marker.start())
    close_pos = find_matching_brace(text, open_pos)
    body = text[open_pos + 1 : close_pos]

    if "Step 155 compatibility constructor" not in body:
        ctor = r'''

    // Step 155 compatibility constructor for legacy nine-field event literals.
    InputEvent() noexcept = default;

    InputEvent(
        int type,
        float a,
        float b,
        float c,
        float d,
        int code,
        int button,
        int modifiers,
        bool pressed
    ) noexcept {
        struct LegacyInputEvent {
            int type;
            float a;
            float b;
            float c;
            float d;
            int code;
            int button;
            int modifiers;
            bool pressed;
        } legacy{type, a, b, c, d, code, button, modifiers, pressed};

        static_assert(sizeof(LegacyInputEvent) >= sizeof(int) * 4 + sizeof(float) * 4,
                      "Unexpected native event payload layout");
        std::memset(this, 0, sizeof(*this));
        std::memcpy(this, &legacy, sizeof(legacy) < sizeof(*this) ? sizeof(legacy) : sizeof(*this));
    }
'''
        text = text[:close_pos] + ctor + text[close_pos:]
    elif "InputEvent() noexcept = default;" not in body:
        # Existing compatibility constructor makes InputEvent non-aggregate;
        # retain value-initialization sites such as InputEvent e{} by restoring
        # an explicit default constructor.
        text = text[:close_pos] + "\n\n    InputEvent() noexcept = default;\n" + text[close_pos:]

    # NDK 27 treats jboolean -> bool in braced constructor arguments as a
    # narrowing conversion. Make the JNI boundary conversion explicit.
    text, mouse_casts = re.subn(
        r"(push\(\{1, x, y, dx, dy, 0, button, 0, )down(\}\);)",
        r"\1static_cast<bool>(down)\2",
        text,
    )
    text, key_casts = re.subn(
        r"(push\(\{2, static_cast<float>\(modifiers\), 0, 0, 0, key, 0, 0, )down(\}\);)",
        r"\1static_cast<bool>(down)\2",
        text,
    )
    text, gamepad_casts = re.subn(
        r"(push\(\{4, 0, 0, 0, 0, button, 0, 0, )down(\}\);)",
        r"\1static_cast<bool>(down)\2",
        text,
    )
    if mouse_casts + key_casts + gamepad_casts < 3:
        raise SystemExit(
            "Expected all three JNI jboolean event pushes to receive explicit bool casts"
        )

    if "#include <cstring>" not in text:
        includes = list(re.finditer(r"^#include\s+<[^>]+>\s*$", text, re.MULTILINE))
        if not includes:
            raise SystemExit("No C++ include block found")
        insert_at = includes[-1].end()
        text = text[:insert_at] + "\n#include <cstring>" + text[insert_at:]

    if text == original:
        raise SystemExit("Step 155 C++ repair made no changes")

    cpp.write_text(text, encoding="utf-8")
    print(f"Repaired native bridge: {cpp}")
    print(f"- removed {removed} stale stopInputPump(true) calls")
    print("- ensured InputEvent has explicit default and nine-field compatibility constructors")
    print("- added explicit bool casts for JNI jboolean event pushes")


if __name__ == "__main__":
    main()
