#!/usr/bin/env python3
"""Fail closed if critical CraftDroid source/build files disappear.

The repository keeps the original launcher implementation in the Step153 source
archive and the authoritative build materializes that archive into ``droid-src``.
Generated-only sources are therefore checked inside the archive and, once
materialized, inside ``droid-src``.
"""
from pathlib import Path
import sys
import zipfile

ROOT_FILES = (
    "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip",
    ".github/workflows/step257-resilient-build.yml",
    "tools/ci/repair_step349_final_generated_compile.py",
    "tools/ci/apply_step352_real_cosmetic_picker_callback.py",
    "tools/ci/verify_step337_microsoft_signin_gui.py",
    "tools/ci/verify_important_feature_coverage.py",
    "tools/ci/verify_step350_ci_invariants.py",
    "tools/ci/verify_critical_repository_files.py",
)

GENERATED_FILES = (
    "app/src/main/java/com/example/auth/MicrosoftAuthManager.kt",
    "app/src/main/java/com/example/auth/MinecraftAuthManager.kt",
    "app/src/main/java/com/example/auth/ElyByAccountProvider.kt",
    "app/src/main/java/com/example/auth/SecureAccountStorage.kt",
    "app/src/main/java/com/example/input/ControlAction.kt",
    "app/src/main/java/com/example/input/TouchInputManager.kt",
    "app/src/main/java/com/example/input/ControlLayout.kt",
    "app/src/main/java/com/example/input/ControlLayoutStorage.kt",
    "app/src/main/java/com/example/game/TouchControlsOverlayView.kt",
    "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchCommandBuilder.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchHandoff.kt",
    "app/src/main/java/com/example/launcher/LaunchPreflight.kt",
    "app/src/main/java/com/example/minecraft/GameInstallationVerifier.kt",
    "app/src/main/java/com/example/runtime/JavaRuntimeManager.kt",
    "app/src/main/java/com/example/renderer/MinecraftPerformanceTuner.kt",
)


def normalize_zip_name(name: str) -> str:
    return name.lstrip("./").replace("\\", "/")


def archive_contains_required_files(archive: Path) -> list[str]:
    with zipfile.ZipFile(archive) as zf:
        names = {normalize_zip_name(n) for n in zf.namelist()}
    missing: list[str] = []
    for required in GENERATED_FILES:
        if required in names:
            continue
        # Some generated ZIPs have a single top-level project folder. Accept that
        # layout while still requiring the exact protected relative path.
        suffix = "/" + required
        if not any(name.endswith(suffix) for name in names):
            missing.append(required)
    return missing


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]).resolve()
    missing = [rel for rel in ROOT_FILES if not (root / rel).is_file()]
    if missing:
        print("[critical-files] FAILED: root files missing")
        for rel in missing:
            print(f"[critical-files] missing: {rel}")
        return 1

    archive = root / "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip"
    bad = []
    if archive.stat().st_size < 1024:
        bad.append("source archive is unexpectedly tiny")
    else:
        try:
            missing_archive = archive_contains_required_files(archive)
        except (OSError, zipfile.BadZipFile) as exc:
            bad.append(f"source archive cannot be read as ZIP: {exc}")
        else:
            if missing_archive:
                bad.append("source archive is missing protected files: " + ", ".join(missing_archive))

    workflow = root / ".github/workflows/step257-resilient-build.yml"
    workflow_text = workflow.read_text(encoding="utf-8", errors="replace")
    if "gradle-version: '9.6.0'" not in workflow_text:
        bad.append("authoritative workflow lost direct Gradle 9.6.0 setup")
    if "Upload APK" not in workflow_text or ":app:assembleDebug" not in workflow_text:
        bad.append("authoritative workflow lost APK build/upload gates")

    generated = root / "droid-src"
    if generated.is_dir():
        missing_generated = [rel for rel in GENERATED_FILES if not (generated / rel).is_file()]
        if missing_generated:
            bad.append("generated source is missing: " + ", ".join(missing_generated))

    if bad:
        print("[critical-files] FAILED")
        for item in bad:
            print(f"[critical-files] {item}")
        return 1

    state = " + generated source" if generated.is_dir() else ""
    print(f"[critical-files] PASS: {len(ROOT_FILES)} root files and {len(GENERATED_FILES)} protected generated files preserved{state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
