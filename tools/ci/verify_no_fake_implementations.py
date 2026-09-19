#!/usr/bin/env python3
"""Fail shipped generated Android source if live UI claims a fake implementation."""
from pathlib import Path
import sys

EARLY_FORBIDDEN = (
    'utilityDialog = "Store"',
    'utilityDialog = "Events"',
    'utilityDialog = "Leaderboard"',
    'utilityDialog = "Events"',
    'utilityDialog = "Leaderboard"',
    "future online integration",
    "ready for future online integration",
    "ResourcePill(\"●\", \"1,250\"",
    "Math.random()",
    "new java.util.Random(",
)

FINAL_ONLY = (
    "managed-on-demand",
    "components_extracted",
    "bootstrapComplete()",
    "showBootstrapGate()",
)

REQUIRED = (
    ("https://api.modrinth.com/v2/search", "real Modrinth discovery"),
    ("version_manifest_v2.json", "real Mojang version manifest"),
    ("step480PingServer", "real Minecraft server-list ping"),
    ("ProcessBuilder(", "real Java process/smoke-test path"),
)

def main():
    final_mode = "--final" in sys.argv[1:]
    positional = [x for x in sys.argv[1:] if x != "--final"]
    root = Path(positional[0] if positional else "droid-src").resolve()
    java_root = root / "app/src/main/java"
    if not java_root.is_dir():
        raise SystemExit("[no-fake] Android source root missing")
    files = [p for p in java_root.rglob("*") if p.suffix in {".kt", ".java", ".cpp", ".h"}]
    combined = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in files)

    bad = [needle for needle in EARLY_FORBIDDEN if needle in combined]
    if final_mode:
        bad.extend(needle for needle in FINAL_ONLY if needle in combined)
    if bad:
        raise SystemExit("[no-fake] forbidden live implementation markers: " + ", ".join(bad))

    if final_mode:
        missing = [label for needle, label in REQUIRED if needle not in combined]
        if missing:
            raise SystemExit("[no-fake] required real implementation missing: " + ", ".join(missing))

    ui = list(java_root.rglob("DroidLauncherUiActivity.kt"))
    if len(ui) == 1:
        text = ui[0].read_text(encoding="utf-8", errors="ignore")
        if "CURSEFORGE" in text and "api.curseforge.com" not in text:
            raise SystemExit("[no-fake] CurseForge is advertised without a real CurseForge API implementation")
        if 'text = "Online"' in text or 'setText("Online")' in text:
            raise SystemExit("[no-fake] static Online server status is not allowed")
        if 'text = "Installed"' in text and "isArtifactHealthy" not in text:
            raise SystemExit("[no-fake] static Installed state lacks an integrity-backed source")

    print("[no-fake] PASS" + (" · final real-feature gate" if final_mode else " · early fake/stub gate"))

if __name__ == "__main__":
    main()
