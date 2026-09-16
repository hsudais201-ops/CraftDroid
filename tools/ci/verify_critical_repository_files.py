#!/usr/bin/env python3
"""Fail closed if a critical CraftDroid source/build file disappears."""
from pathlib import Path
import sys

CRITICAL_FILES = (
    "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip",
    ".github/workflows/step257-resilient-build.yml",
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
    "tools/ci/repair_step349_final_generated_compile.py",
    "tools/ci/apply_step352_real_cosmetic_picker_callback.py",
    "tools/ci/verify_step337_microsoft_signin_gui.py",
    "tools/ci/verify_important_feature_coverage.py",
    "tools/ci/verify_step350_ci_invariants.py",
)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]).resolve()
    missing = [rel for rel in CRITICAL_FILES if not (root / rel).is_file()]
    if missing:
        print("[critical-files] FAILED")
        for rel in missing:
            print(f"[critical-files] missing: {rel}")
        return 1
    bad = []
    archive = root / "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip"
    if archive.stat().st_size < 1024:
        bad.append("source archive is unexpectedly tiny")
    workflow = root / ".github/workflows/step257-resilient-build.yml"
    workflow_text = workflow.read_text(encoding="utf-8", errors="replace")
    if "gradle-version: '9.6.0'" not in workflow_text:
        bad.append("authoritative workflow lost direct Gradle 9.6.0 setup")
    if "Upload APK" not in workflow_text or ":app:assembleDebug" not in workflow_text:
        bad.append("authoritative workflow lost APK build/upload gates")
    if bad:
        print("[critical-files] FAILED")
        for item in bad:
            print(f"[critical-files] {item}")
        return 1
    print(f"[critical-files] PASS: {len(CRITICAL_FILES)} critical files preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
