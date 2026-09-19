# CraftDroid Step 13 — Crash / Exit Diagnostics

## Implemented
- Detects Minecraft crash reports in `crash-reports/`.
- Detects HotSpot `hs_err_pid*.log` native fatal-error reports.
- Captures embedded JVM stdout/stderr.
- Builds a timestamped diagnostic summary under `Minecraft/crash-diagnostics/`.
- Passes the newest Minecraft crash report into `CrashAnalyzer`.
- Recognizes SIGSEGV/JVM fatal native crashes.
- Keeps sensitive authentication values redacted by `LauncherLogger`.

## Why this matters
PojavLauncher reports rely heavily on `latestlog.txt` and crash-report files when diagnosing game exits; native JVM crashes can additionally produce `hs_err_pid*.log`. CraftDroid now preserves these artifacts instead of reporting only a generic exit code.

## Limitation
This step does not claim to automatically fix a native crash. The diagnostics make the failing layer identifiable after a real-device run.
