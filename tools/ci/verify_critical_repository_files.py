#!/usr/bin/env python3
"""Fail closed if critical CraftDroid source/build files disappear.

The project has two intentional source layers: the Step153 archive provides the
baseline launcher, while the repository's app tree provides newer shared
implementation files that the authoritative Step257 workflow copies into the
generated tree. This verifier checks both layers without pretending every newer
file must already exist in the old archive.
"""
from pathlib import Path
import sys
import zipfile

ROOT_FILES = (
    "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip",
    ".github/workflows/step406-resilient-build.yml",
    "tools/ci/repair_step349_final_generated_compile.py",
    "tools/ci/apply_step352_real_cosmetic_picker_callback.py",
    "tools/ci/repair_step357_final_scope_compile.py",
    "tools/ci/verify_step337_microsoft_signin_gui.py",
    "tools/ci/verify_important_feature_coverage.py",
    "tools/ci/verify_step350_ci_invariants.py",
    "tools/ci/apply_step375_custom_ui.py",
    "tools/ci/apply_step376_low_ram_ui.py",
    "tools/ci/apply_step382_settings_cleanup.py",
    "tools/ci/apply_step391_final_content_picker.py",
    "tools/ci/apply_step395_low_ram_memory_settings.py",
    "tools/ci/verify_critical_repository_files.py",
)

SHARED_SOURCE_FILES = (
    "app/src/main/java/com/example/launcher/LaunchArgumentResolver.kt",
    "app/src/main/java/com/example/launcher/LaunchArgumentsValidator.kt",
    "app/src/main/java/com/example/launcher/LaunchArtifactResolver.kt",
    "app/src/main/java/com/example/launcher/MinecraftStorageResolver.kt",
    "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchPaths.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchCommandBuilder.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchHandoff.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchHandoffValidator.kt",
    "app/src/main/java/com/example/launcher/MinecraftRuntimeProfile.kt",
    "app/src/main/java/com/example/launcher/MinecraftLatestVersionManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftContentManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftModpackManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftLoaderProfile.kt",
    "app/src/main/java/com/example/launcher/LauncherBackgroundInstallController.kt",
    "app/src/main/java/com/example/launcher/DroidLauncherUpdateManager.kt",
    "app/src/main/java/com/example/logs/MinecraftProcessMonitor.kt",
    "app/src/main/java/com/example/renderer/PerformanceProfile.kt",
    "app/src/main/java/com/example/renderer/MinecraftPerformanceTuner.kt",
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


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]).resolve()
    bad: list[str] = []

    missing_root = [rel for rel in ROOT_FILES if not (root / rel).is_file()]
    if missing_root:
        bad.append("missing root files: " + ", ".join(missing_root))

    missing_shared = [rel for rel in SHARED_SOURCE_FILES if not (root / rel).is_file()]
    if missing_shared:
        bad.append("missing repository-owned shared sources: " + ", ".join(missing_shared))

    archive = root / "CraftDroid_Launcher_2.4_GitHubActions_Step153.zip"
    if archive.is_file():
        if archive.stat().st_size < 1024:
            bad.append("source archive is unexpectedly tiny")
        else:
            try:
                with zipfile.ZipFile(archive) as zf:
                    if zf.testzip() is not None:
                        bad.append("source archive contains a corrupt member")
            except (OSError, zipfile.BadZipFile) as exc:
                bad.append(f"source archive cannot be read as ZIP: {exc}")

    workflow = root / ".github/workflows/step406-resilient-build.yml"
    if workflow.is_file():
        workflow_text = workflow.read_text(encoding="utf-8", errors="replace")
        required_markers = (
            "gradle-version: '9.6.0'",
            "validate-wrappers: false",
            ":app:lintDebug",
            ":app:testDebugUnitTest",
            ":app:assembleDebug",
            "Upload APK",
        )
        for marker in required_markers:
            if marker not in workflow_text:
                bad.append(f"authoritative workflow lost required marker: {marker}")

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
    print(f"[critical-files] PASS: {len(ROOT_FILES)} root files + {len(SHARED_SOURCE_FILES)} shared sources preserved{state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
