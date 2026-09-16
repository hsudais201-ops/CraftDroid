#!/usr/bin/env python3
"""Verify that the generated launcher still contains every major requested subsystem.

This is deliberately a contract audit, not a fake implementation: it checks for the
real source files/classes and important integration markers that the launcher build
is expected to preserve after its many code-generation/repair stages.
"""
from pathlib import Path
import re
import sys

REQUIRED_FILES = (
    "app/src/main/java/com/example/input/TouchInputManager.kt",
    "app/src/main/java/com/example/input/ControlLayout.kt",
    "app/src/main/java/com/example/input/ControlLayoutStorage.kt",
    "app/src/main/java/com/example/game/TouchControlsOverlayView.kt",
    "app/src/main/java/com/example/auth/MicrosoftAuthManager.kt",
    "app/src/main/java/com/example/auth/MinecraftAuthManager.kt",
    "app/src/main/java/com/example/auth/ElyByAccountProvider.kt",
    "app/src/main/java/com/example/auth/SecureAccountStorage.kt",
    "app/src/main/java/com/example/skin/SkinManager.kt",
    "app/src/main/java/com/example/launcher/WorldManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftContentManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftModpackManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftLoaderProfile.kt",
    "app/src/main/java/com/example/launcher/MinecraftRuntimeProfile.kt",
    "app/src/main/java/com/example/launcher/MinecraftVersionInstallManager.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchCommandBuilder.kt",
    "app/src/main/java/com/example/launcher/MinecraftLaunchHandoff.kt",
    "app/src/main/java/com/example/launcher/LaunchPreflight.kt",
    "app/src/main/java/com/example/minecraft/GameInstallationVerifier.kt",
    "app/src/main/java/com/example/runtime/JavaRuntimeManager.kt",
    "app/src/main/java/com/example/renderer/MinecraftPerformanceTuner.kt",
)

REQUIRED_TEXT = {
    "app/src/main/java/com/example/input/ControlAction.kt": (
        "FORWARD", "BACKWARD", "LEFT", "RIGHT", "JOYSTICK_MOVE", "JUMP",
        "SNEAK", "SPRINT", "ATTACK", "USE", "DROP", "INVENTORY", "CHAT", "PAUSE",
        "CAMERA_LOOK",
    ),
    "app/src/main/java/com/example/input/TouchInputManager.kt": (
        "beginEditorGesture", "endEditorGesture", "undoEditorChange", "redoEditorChange",
        "duplicateControl", "deleteControl", "setOrientation", "setSnapGridPercent",
    ),
    "app/src/main/java/com/example/input/ControlLayoutStorage.kt": (
        "saveState", "loadAllProfiles", "validateAndImportProfile", "exportProfileToJson",
    ),
    "app/src/main/java/com/example/auth/MicrosoftAuthManager.kt": (
        "requestDeviceCode", "pollForToken", "refreshMicrosoftToken",
        "oauth2/v2.0/devicecode", "oauth2/v2.0/token",
    ),
    "app/src/main/java/com/example/auth/ElyByAccountProvider.kt": (
        "buildAuthorizationUrl", "refreshSession",
    ),
    "app/src/main/java/com/example/skin/SkinManager.kt": (
        "loadSkinBitmap", "SkinTextureGenerator",
    ),
    "app/src/main/java/com/example/launcher/MinecraftLaunchHandoff.kt": (
        "launch", "validate",
    ),
}


def read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise SystemExit(f"[coverage] missing required file: {rel}")
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    errors = []

    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            errors.append(f"missing file: {rel}")

    for rel, needles in REQUIRED_TEXT.items():
        if not (root / rel).is_file():
            continue
        text = read(root, rel)
        for needle in needles:
            if needle not in text:
                errors.append(f"{rel}: missing integration marker {needle!r}")

    ui_candidates = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(ui_candidates) != 1:
        errors.append(f"expected exactly one DroidLauncherUiActivity.kt, found {len(ui_candidates)}")
    else:
        ui = ui_candidates[0].read_text(encoding="utf-8", errors="replace")
        ui_checks = (
            '"Game"', '"Accounts"', '"Features"', '"Servers"', '"Settings"',
            'showPage("Game")', 'setOnClickListener { showPage("Features") }',
            'private fun serverPrefs()', 'private fun getSavedServers()',
            'private fun getServerName(', 'private fun getServerStatus(',
            'private fun selectServer(', 'private fun showServerDialog(',
        )
        for needle in ui_checks:
            if needle not in ui:
                errors.append(f"DroidLauncherUiActivity.kt: missing {needle!r}")
        if "showBootstrapGate" in ui or "BootstrapComponent" in ui:
            errors.append("DroidLauncherUiActivity.kt: obsolete fake bootstrap gate remains")
        if re.search(r"(?m)^\s*singleLine\s*=", ui):
            errors.append("DroidLauncherUiActivity.kt: Android EditText singleLine property remains")

    screen_files = list((root / "app/src/main/java").rglob("CustomizeControlsScreen.kt"))
    if len(screen_files) != 1:
        errors.append(f"expected exactly one CustomizeControlsScreen.kt, found {len(screen_files)}")
    else:
        screen = screen_files[0].read_text(encoding="utf-8", errors="replace")
        for needle in ("ADD CONTROL", "RESET", "SAVE", "duplicateControl", "deleteControl", "Slider", "onDrag", "opacity"):
            if needle not in screen:
                errors.append(f"CustomizeControlsScreen.kt: missing {needle!r}")

    if errors:
        print("[coverage] FAILED")
        for error in errors:
            print(f"[coverage] {error}")
        return 1

    print(f"[coverage] PASS: {len(REQUIRED_FILES)} required subsystem files and all integration contracts are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
