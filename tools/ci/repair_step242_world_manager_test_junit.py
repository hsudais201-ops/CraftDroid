#!/usr/bin/env python3
"""Step 242: make the Step 177 world-manager fixture use the project's JUnit4 test stack."""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = root / "app/src/test/java/com/example/launcher/WorldManagerStep177Test.kt"
    if not path.is_file():
        raise SystemExit(f"[step242] missing generated test: {path}")
    s = path.read_text(encoding="utf-8")
    s = s.replace("import kotlin.test.Test\n", "import org.junit.Test\n")
    s = s.replace("import kotlin.test.assertEquals\n", "import org.junit.Assert.assertEquals\n")
    s = s.replace("import kotlin.test.assertTrue\n", "import org.junit.Assert.assertTrue\n")
    # kotlin.test's assertFailsWith is not guaranteed to be on the generated
    # project's JVM test runtime. Keep the test dependency-free beyond JUnit4.
    s = s.replace("import kotlin.test.assertFailsWith\n", "")
    old = '''            assertFailsWith<IllegalArgumentException> { WorldManager(root).importWorld(archive, "Evil") }\n'''
    new = '''            try {
                WorldManager(root).importWorld(archive, "Evil")
                throw AssertionError("Expected unsafe archive to be rejected")
            } catch (_: IllegalArgumentException) {
                // expected
            }
'''
    if old in s:
        s = s.replace(old, new, 1)
    path.write_text(s, encoding="utf-8")

    checks = (
        "import org.junit.Test",
        "import org.junit.Assert.assertEquals",
        "import org.junit.Assert.assertTrue",
        "Expected unsafe archive to be rejected",
    )
    for needle in checks:
        if needle not in s:
            raise SystemExit(f"[step242] missing JUnit4 migration contract: {needle}")
    if "kotlin.test.Test" in s or "kotlin.test.assert" in s:
        raise SystemExit("[step242] kotlin.test imports remain")
    print("[step242] WorldManagerStep177Test migrated to project's JUnit4 dependency")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
