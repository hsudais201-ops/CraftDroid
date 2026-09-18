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
    changed = False

    malformed = """                lastKnownLogLength = currentLogLength
            }

            val state = NativeGameBridge.javaState()
"""
    corrected = """                }
                lastKnownLogLength = currentLogLength
            }

            val state = NativeGameBridge.javaState()
"""
    if malformed in text:
        text = text.replace(malformed, corrected, 1)
        changed = True
        print("[step426] repaired missing closing brace in MinecraftProcessMonitor")

    if "currentLogLength != lastKnownLogLength || currentLogLength < 0L" in text:
        text = text.replace(
            "currentLogLength != lastKnownLogLength || currentLogLength < 0L",
            "currentLogLength != lastKnownLogLength",
            1,
        )
        changed = True
        print("[step426] stopped polling a nonexistent Minecraft log every cycle")

    assignment_inside_callback = """                }
                lastKnownLogLength = currentLogLength
            }

            val state = NativeGameBridge.javaState()
"""
    assignment_outside_callback = """                }
            }
            lastKnownLogLength = currentLogLength

            val state = NativeGameBridge.javaState()
"""
    if assignment_inside_callback in text:
        text = text.replace(assignment_inside_callback, assignment_outside_callback, 1)
        changed = True
        print("[step426] moved log-length state update outside the read callback")

    if "const val MAX_EVENT_LOG_BYTES" not in text:
        text = text.replace(
            "    private var lastLogChangeEventAt = 0L",
            "    private var lastLogChangeEventAt = 0L\\n\\n    private companion object {\\n        const val MAX_EVENT_LOG_BYTES = 64 * 1024L\\n        const val EVENT_LOG_TAIL_BYTES = 48 * 1024L\\n    }",
            1,
        )
        changed = True
        print("[step426] event-log size bounds installed")

    if "import java.io.FileOutputStream" not in text:
        text = text.replace(
            "import java.io.File",
            "import java.io.File\\nimport java.io.FileOutputStream",
            1,
        )
        changed = True

    # Normalize malformed monitor-loop boundaries structurally rather than relying
    # on one exact indentation string. Older generators sometimes leave repeated
    # closing braces immediately before lastKnownLogLength.
    lines = text.splitlines()
    removed = 0
    last_idx = next((i for i, line in enumerate(lines)
                     if "lastKnownLogLength = currentLogLength" in line), -1)
    if last_idx >= 2:
        while last_idx >= 2:
            prev = lines[last_idx - 1]
            prev2 = lines[last_idx - 2]
            indent_prev = len(prev) - len(prev.lstrip(" "))
            indent_prev2 = len(prev2) - len(prev2.lstrip(" "))
            indent_target = len(lines[last_idx]) - len(lines[last_idx].lstrip(" "))
            if (
                prev.strip() == "}"
                and prev2.strip() == "}"
                and indent_prev2 == indent_prev
                and indent_prev > indent_target
            ):
                del lines[last_idx - 1]
                removed += 1
                last_idx -= 1
            else:
                break
        if removed:
            text = "\n".join(lines) + ("\n" if path.read_text(encoding="utf-8").endswith("\n") else "")
            changed = True
            print(f"[step433] removed {removed} structurally duplicated monitor brace(s)")

    old_emit = """    private fun emit(type: EventType, message: String) {
        val event = Event(type, message)
        onEvent(event)
        runCatching {
            diagnosticsDir.mkdirs()
            File(diagnosticsDir, "step165-events.log").appendText(\"${event.timestampMs} [${event.type}] ${event.message}\\n\")
        }
        when (type) {
"""
    new_emit = """    private fun emit(type: EventType, message: String) {
        val event = Event(type, message)
        runCatching { onEvent(event) }
            .onFailure { LauncherLogger.warn("Minecraft monitor listener failed: ${it.message}") }
        runCatching {
            diagnosticsDir.mkdirs()
            appendBoundedEventLog(
                File(diagnosticsDir, "step165-events.log"),
                "${event.timestampMs} [${event.type}] ${event.message}\\n"
            )
        }
        when (type) {
"""
    if old_emit in text:
        text = text.replace(old_emit, new_emit, 1)
        changed = True
        print("[step426] monitor listener and bounded event logging installed")

    if "private fun appendBoundedEventLog(file: File, line: String)" not in text:
        helper = """    private fun appendBoundedEventLog(file: File, line: String) {
        FileOutputStream(file, true).use { output ->
            output.write(line.toByteArray(Charsets.UTF_8))
        }
        if (file.length() <= MAX_EVENT_LOG_BYTES) return

        val tail = runCatching {
            file.inputStream().use { input ->
                val length = file.length()
                var remaining = (length - EVENT_LOG_TAIL_BYTES).coerceAtLeast(0L)
                while (remaining > 0L) {
                    val skipped = input.skip(minOf(remaining, 64L * 1024L))
                    if (skipped <= 0L) break
                    remaining -= skipped
                }
                val buffer = ByteArray(minOf(EVENT_LOG_TAIL_BYTES, length).toInt())
                val read = input.read(buffer)
                if (read <= 0) "" else String(buffer, 0, read, Charsets.UTF_8)
            }
        }.getOrDefault("")

        if (tail.isNotEmpty()) {
            file.outputStream().use { it.write(tail.toByteArray(Charsets.UTF_8)) }
        } else {
            file.delete()
        }
    }

"""
        anchor = "    private fun emit(type: EventType, message: String) {"
        pos = text.find(anchor)
        if pos < 0:
            raise SystemExit("[step426] emit anchor missing")
        text = text[:pos] + helper + text[pos:]
        changed = True

    if changed:
        path.write_text(text, encoding="utf-8")
    print("[step426] Minecraft monitor low-RAM hardening checked")

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
    if "if (currentLogLength != lastKnownLogLength)" not in monitor_text:
        raise SystemExit("[step426] change-detection poll guard missing")
    if "appendBoundedEventLog(" not in monitor_text:
        raise SystemExit("[step426] bounded event log helper missing")
    monitor_lines = monitor_text.splitlines()
    last_idx = next((i for i, line in enumerate(monitor_lines)
                     if "lastKnownLogLength = currentLogLength" in line), -1)
    if last_idx < 2:
        raise SystemExit("[step433] monitor log-length state anchor missing")
    prev = monitor_lines[last_idx - 1]
    prev2 = monitor_lines[last_idx - 2]
    indent_prev = len(prev) - len(prev.lstrip(" "))
    indent_prev2 = len(prev2) - len(prev2.lstrip(" "))
    if prev.strip() != "}" or prev2.strip() != "}" or indent_prev2 == indent_prev or indent_prev2 <= indent_prev:
        raise SystemExit("[step433] malformed monitor-loop boundary remains after normalization")
    if "MAX_EVENT_LOG_BYTES" not in monitor_text:
        raise SystemExit("[step426] event-log bound constant missing")

    print("[step426] low-RAM diagnostics hardening contract verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
