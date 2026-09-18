#!/usr/bin/env python3
"""Step 426: harden generated diagnostics for constrained Android devices.

This repair is intentionally small and idempotent. It fixes the Step 423/424
Minecraft log monitor block closure, bounds crash-diagnostics tail reads, and
avoids recursive filesystem walks when looking for the latest HotSpot crash.
"""

from pathlib import Path
import sys


MONITOR_REL = Path("app/src/main/java/com/example/logs/MinecraftProcessMonitor.kt")
CRASH_REL = Path("app/src/main/java/com/example/logs/CrashDiagnostics.kt")
RECOVERY_REL = Path("app/src/main/java/com/example/logs/LaunchRecoveryPolicy.kt")


def patch_monitor(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    malformed = """                lastKnownLogLength = currentLogLength
            }

            val state = NativeGameBridge.javaState()
"""
    corrected = """                lastKnownLogLength = currentLogLength
            }
            }

            val state = NativeGameBridge.javaState()
"""
    if malformed in text:
        text = text.replace(malformed, corrected, 1)
        path.write_text(text, encoding="utf-8")
        print("[step426] repaired missing closing brace in MinecraftProcessMonitor")
    elif corrected in text:
        print("[step426] MinecraftProcessMonitor brace repair already present")
    else:
        raise SystemExit("[step426] MinecraftProcessMonitor expected block anchor not found")


def patch_crash_diagnostics(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """                    val text = runCatching { file.readText() }.getOrDefault("")
                    w.println(text.takeLast(12000))
"""
    new = """                    val text = runCatching { tailText(file, 12000) }.getOrDefault("")
                    w.println(text)
"""
    if old in text:
        text = text.replace(old, new, 1)
        helper = """    private fun tailText(file: File, maxChars: Int): String {
        if (!file.isFile || maxChars <= 0) return ""
        val maxBytes = 64L * 1024L
        val length = runCatching { file.length() }.getOrDefault(0L)
        if (length <= 0L) return ""

        return runCatching {
            file.inputStream().use { input ->
                var remaining = (length - maxBytes).coerceAtLeast(0L)
                while (remaining > 0L) {
                    val requested = minOf(remaining, 64L * 1024L)
                    val skipped = input.skip(requested)
                    if (skipped <= 0L) break
                    remaining -= skipped
                }

                val buffer = ByteArray(minOf(maxBytes, length).toInt())
                val read = input.read(buffer)
                if (read <= 0) "" else String(buffer, 0, read, Charsets.UTF_8).takeLast(maxChars)
            }
        }.getOrDefault("")
    }

"""
        anchor = "    private fun newest(dir: File, glob: String): File? {"
        if anchor not in text:
            raise SystemExit("[step426] CrashDiagnostics newest() anchor missing")
        text = text.replace(anchor, helper + anchor, 1)
        path.write_text(text, encoding="utf-8")
        print("[step426] bounded CrashDiagnostics tail reader installed")
    elif "tailText(file, 12000)" in text and "private fun tailText(file: File, maxChars: Int)" in text:
        print("[step426] CrashDiagnostics bounded tail reader already present")
    else:
        raise SystemExit("[step426] CrashDiagnostics tail anchor not found")


def patch_recovery(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    old = """        val latest = rootDir.walkTopDown()
            .filter { it.isFile }
            .filter { it.name.startsWith("hs_err_pid") || it.name.contains("hotspot", ignoreCase = true) }
            .maxByOrNull { it.lastModified() }
            ?: return requested
"""
    new = """        val candidateDirs = listOf(
            rootDir,
            rootDir.resolve("crash-reports"),
            rootDir.resolve("logs"),
            rootDir.resolve("crash-diagnostics")
        )
        val latest = candidateDirs
            .asSequence()
            .flatMap { it.listFiles()?.asSequence() ?: emptySequence() }
            .filter { it.isFile }
            .filter { it.name.startsWith("hs_err_pid") || it.name.contains("hotspot", ignoreCase = true) }
            .maxByOrNull { it.lastModified() }
            ?: return requested
"""
    if old in text:
        text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
        print("[step426] replaced recursive HotSpot crash scan with bounded directory scan")
    elif "val candidateDirs = listOf(" in text and "flatMap { it.listFiles()?.asSequence()" in text:
        print("[step426] bounded HotSpot crash scan already present")
    else:
        raise SystemExit("[step426] LaunchRecoveryPolicy recursive scan anchor not found")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()

    monitor = root / MONITOR_REL
    crash = root / CRASH_REL
    recovery = root / RECOVERY_REL

    for path in (monitor, crash, recovery):
        if not path.is_file():
            raise SystemExit(f"[step426] required generated source missing: {path}")

    patch_monitor(monitor)
    patch_crash_diagnostics(crash)
    patch_recovery(recovery)

    crash_text = crash.read_text(encoding="utf-8")
    recovery_text = recovery.read_text(encoding="utf-8")
    monitor_text = monitor.read_text(encoding="utf-8")

    if "tailText(file, 12000)" not in crash_text:
        raise SystemExit("[step426] bounded crash tail call missing")
    if "ByteArray(minOf(maxBytes, length).toInt())" not in crash_text:
        raise SystemExit("[step426] crash diagnostics memory bound missing")
    if "rootDir.walkTopDown()" in recovery_text:
        raise SystemExit("[step426] recursive HotSpot scan still present")
    if "val candidateDirs = listOf(" not in recovery_text:
        raise SystemExit("[step426] bounded HotSpot candidate directories missing")
    if monitor_text.count("val state = NativeGameBridge.javaState()") != 1:
        raise SystemExit("[step426] unexpected monitor state anchor count")

    print("[step426] low-RAM diagnostics hardening contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
