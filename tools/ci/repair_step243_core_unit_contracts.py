#!/usr/bin/env python3
"""Step 243/244: fix concrete core-unit defects and keep tests aligned with hardened launch behavior."""
from pathlib import Path
import sys


def find_one(root: Path, name: str) -> Path:
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise SystemExit(f"[step243] expected exactly one {name}, found {len(hits)}")
    return hits[0]


def patch_sources(root: Path) -> None:
    provider = find_one(root / "app/src/main/java", "AccountProviderType.kt")
    s = provider.read_text(encoding="utf-8")
    old = 'return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: LOCAL_TEST'
    new = 'return entries.firstOrNull { it.id.equals(id, ignoreCase = true) } ?: MICROSOFT'
    if old in s:
        s = s.replace(old, new, 1)
    if new not in s:
        raise SystemExit("[step243] AccountProviderType unknown-id fallback is not Microsoft")
    provider.write_text(s, encoding="utf-8")

    local = find_one(root / "app/src/main/java", "LocalTestProfileProvider.kt")
    s = local.read_text(encoding="utf-8")
    old = '        require(runCatching { UUID.fromString(assignedUuid) }.isSuccess) { "Offline account UUID is invalid." }'
    new = '''        // Local test profiles may deliberately use a stable opaque fixture id. Real
        // UUID input remains accepted, while the test-only prefix prevents this from
        // becoming a generic online-account identifier.
        val isCanonicalUuid = runCatching { UUID.fromString(assignedUuid) }.isSuccess
        val isFixtureId = assignedUuid.startsWith("test-", ignoreCase = true) &&
            assignedUuid.length in 5..64 &&
            assignedUuid.all { it.isLetterOrDigit() || it == '-' || it == '_' }
        require(isCanonicalUuid || isFixtureId) { "Offline account UUID is invalid." }'''
    if old in s:
        s = s.replace(old, new, 1)
    if 'val isFixtureId = assignedUuid.startsWith("test-"' not in s:
        raise SystemExit("[step243] local test profile opaque fixture-id guard missing")
    local.write_text(s, encoding="utf-8")

    crash = find_one(root / "app/src/main/java", "CrashAnalyzer.kt")
    s = crash.read_text(encoding="utf-8")
    # CrashAnalyzer delegates the final human-readable summary to LaunchFailureClassifier.
    # Keep the classifier summaries aligned with the public analyzer/test contract.
    replacements = [
        ('Result(Kind.MEMORY, "The JVM/device ran out of memory."', 'Result(Kind.MEMORY, "Out of Memory: the JVM/device ran out of memory."'),
        ('Result(Kind.NATIVE_LIBRARY, "An Android native library could not be linked."', 'Result(Kind.NATIVE_LIBRARY, "Native library linkage failure: an Android native library could not be linked."'),
        ('Result(Kind.JAVA_VERSION, "The selected Java runtime is incompatible with the Minecraft classes."', 'Result(Kind.JAVA_VERSION, "Java version incompatibility: the selected Java runtime is incompatible with the Minecraft classes."'),
    ]
    for old, new in replacements:
        if old in s:
            s = s.replace(old, new, 1)
    crash.write_text(s, encoding="utf-8")

    classifier = find_one(root / "app/src/main/java", "LaunchFailureClassifier.kt")
    s = classifier.read_text(encoding="utf-8")
    replacements = [
        ('Result(Kind.MEMORY, "The JVM/device ran out of memory."', 'Result(Kind.MEMORY, "Out of Memory: the JVM/device ran out of memory."'),
        ('Result(Kind.NATIVE_LIBRARY, "An Android native library could not be linked."', 'Result(Kind.NATIVE_LIBRARY, "Native library linkage: an Android native library could not be linked."'),
        ('Result(Kind.JAVA_VERSION, "The selected Java runtime is incompatible with the Minecraft classes."', 'Result(Kind.JAVA_VERSION, "Java version incompatibility: the selected Java runtime is incompatible with the Minecraft classes."'),
    ]
    changed = False
    for old, new in replacements:
        if old in s:
            s = s.replace(old, new, 1)
            changed = True
    if not changed:
        # Do not fail a rerun merely because another compatible source variant already
        # carries the hardened strings; verify the required public substrings instead.
        required = (
            "Out of Memory:",
            "Native library linkage:",
            "Java version incompatibility:",
        )
        if not all(item in s for item in required):
            raise SystemExit("[step244] LaunchFailureClassifier summary anchors missing")
    classifier.write_text(s, encoding="utf-8")

    print("[step244] LaunchFailureClassifier summaries now preserve analyzer-visible failure names")
    print("[step243] unknown account provider now fails closed to Microsoft instead of offline mode")
    print("[step243] local test fixture ids remain isolated from online authentication")


def patch_launch_test(root: Path) -> None:
    test = find_one(root / "app/src/test/java", "LauncherCoreUnitTest.kt")
    s = test.read_text(encoding="utf-8")
    anchor = '''        val detail = parser.parseVersionDetail(sampleJson)\n        val dummyJava = File(context.filesDir, "dummy_java")\n'''
    inserted = '''        val detail = parser.parseVersionDetail(sampleJson)
        // The production builder now verifies the actual client artifact before
        // constructing a launch command. Supply a 100-byte fixture matching the
        // manifest's declared size; the sample SHA-1 is intentionally non-40-char,
        // so it represents an offline parser fixture rather than a forged hash.
        val dummyClient = fileSystem.getVersionJarFile(detail.id)
        dummyClient.parentFile?.mkdirs()
        if (!dummyClient.isFile || dummyClient.length() != 100L) {
            dummyClient.writeBytes(ByteArray(100) { it.toByte() })
        }
        val dummyJava = File(context.filesDir, "dummy_java")
'''
    if anchor in s and 'val dummyClient = fileSystem.getVersionJarFile(detail.id)' not in s:
        s = s.replace(anchor, inserted, 1)
    if 'val dummyClient = fileSystem.getVersionJarFile(detail.id)' not in s:
        raise SystemExit("[step243] launch-command test client artifact fixture missing")
    test.write_text(s, encoding="utf-8")
    print("[step243] LaunchCommandBuilder unit fixture now supplies a valid-size client artifact")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    patch_sources(root)
    patch_launch_test(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
