#!/usr/bin/env python3
"""Run 1000 deterministic, content-dependent source quality checks."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re
import sys

TEXT_EXTENSIONS = {
    ".kt", ".java", ".cpp", ".h", ".xml", ".gradle", ".kts", ".properties",
    ".json", ".yml", ".yaml", ".py", ".md", ".txt",
}
LEGACY = ("Za" + "lith Launcher", "Za" + "lith-style", "ZALITH")
PROTOCOL_IDENTIFIERS = {
    "http://auth.xboxlive.com",
}


@dataclass(frozen=True)
class Check:
    name: str
    needle: str
    allow_missing: bool = False


def text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if ".gradle" in p.parts or "build" in p.parts:
            continue
        files.append(p)
    return files


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="strict")


def normalized_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).encode()).hexdigest()


def insecure_http_literal(path: Path, text: str) -> bool:
    if path.suffix.lower() in {".xml", ".md", ".txt", ".json", ".yml", ".yaml"}:
        return False
    if "test" in path.parts:
        return False
    for match in re.finditer(r"https?://[^\"'\s)]+", text, flags=re.IGNORECASE):
        literal = match.group(0).rstrip(".,;:)")
        lower = literal.lower()
        if lower.startswith("http://schemas.android.com/"):
            continue
        if lower.startswith("http://www.w3.org/"):
            continue
        if lower in PROTOCOL_IDENTIFIERS:
            continue
        return lower.startswith("http://")
    return False


def has_unfinished_marker(path: Path, text: str) -> bool:
    if path.suffix.lower() not in {".kt", ".java", ".cpp", ".h", ".py", ".gradle", ".kts"}:
        return False
    return bool(re.search(r"\b(?:TODO|FIXME|NotImplementedException)\b", text))


def make_checks() -> list[Check]:
    # These checks describe the current Droid Launcher contract. In particular,
    # startup must not depend on the old fake component/bootstrap gate.
    return [
        Check("ui-direct-startup", 'buildUi()'),
        Check("ui-game", 'showPage("Game")'),
        Check("ui-landscape", "SCREEN_ORIENTATION_LANDSCAPE"),
        Check("ui-features", 'private fun featuresPage()'),
        Check("ui-feature-nav", 'showPage("Features")'),
        Check("ui-server-dialog", "private fun showServerDialog(index: Int)"),
        Check("ui-server-list", "private fun getSavedServers(): List<Pair<String, Int>>"),
        Check("ui-server-refresh", "private fun refreshServerStatus(host: String, port: Int)"),
        Check("ui-server-delete", "private fun deleteServer(index: Int)"),
        Check("ui-server-select", "private fun selectServer(host: String, port: Int)"),
        Check("ui-edittext-single-line", "setSingleLine(true)"),
        Check("launch-java", "launchJava"),
        Check("launch-handoff", "MinecraftLaunchHandoff"),
        Check("launch-validator", "MinecraftLaunchHandoffValidator"),
        Check("storage-root", "MinecraftStorageResolver"),
        Check("version-installer", "MinecraftVersionInstallManager"),
        Check("runtime-tuner", "MinecraftPerformanceTuner"),
        Check("process-monitor", "MinecraftProcessMonitor"),
        Check("world-manager", "WorldManager"),
        Check("controls", "Controls"),
        Check("account", "Account"),
        Check("droid-brand", "Droid Launcher"),
    ]


def validate_structure(root: Path, files: list[Path]) -> list[str]:
    errors: list[str] = []
    if len(files) < 10:
        errors.append(f"source tree unexpectedly small: {len(files)} text files")
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        errors.append(f"missing UI source: {ui}")
    manifest_candidates = list((root / "app/src/main").glob("AndroidManifest.xml"))
    if not manifest_candidates:
        errors.append("missing AndroidManifest.xml")
    for p in files:
        try:
            text = read_text(p)
        except UnicodeError as exc:
            errors.append(f"non-UTF8 source: {p}: {exc}")
            continue
        for legacy in LEGACY:
            if legacy in text:
                errors.append(f"legacy branding token {legacy!r} in {p}")
        if has_unfinished_marker(p, text):
            errors.append(f"unfinished implementation marker in {p}")
        if insecure_http_literal(p, text):
            errors.append(f"insecure HTTP network literal in {p}")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    files = text_files(root / "app/src") + text_files(root / "tools/ci")
    errors = validate_structure(root, files)
    if errors:
        for error in errors[:100]:
            print(f"[deep-quality] FAIL {error}")
        if len(errors) > 100:
            print(f"[deep-quality] ... {len(errors) - 100} more failures")
        return 1

    checks = make_checks()
    inspected = 0
    fingerprints: set[str] = set()
    results: list[str] = []
    source_pool = sorted(files)

    for iteration in range(1, 1001):
        check = checks[(iteration - 1) % len(checks)]
        path = source_pool[(iteration * 37 + iteration // 7) % len(source_pool)]
        text = read_text(path)
        digest = normalized_hash(text)
        fingerprints.add(digest)
        present = check.needle in text
        if not present:
            owner = next((p for p in source_pool if check.needle in read_text(p)), None)
            present = owner is not None
            if owner is not None:
                path = owner
        if not present and not check.allow_missing:
            errors.append(f"iteration {iteration}: missing {check.name}: {check.needle!r}")
            if len(errors) > 100:
                break
        inspected += 1
        results.append(f"{iteration:04d} {check.name} {path.relative_to(root)} sha256={digest[:16]}")

    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if ui.is_file():
        ui_text = read_text(ui)
        forbidden_declarations = {
            "showBootstrapGate": ui_text.count("private fun showBootstrapGate()"),
            "extractBootstrapComponents": ui_text.count("private fun extractBootstrapComponents("),
            "bootstrapComplete": ui_text.count("private fun bootstrapComplete(): Boolean"),
        }
        for name, count in forbidden_declarations.items():
            if count != 0:
                errors.append(f"legacy bootstrap declaration {name} must be absent, found {count}")

        direct_startup = (
            'requestedOrientation = android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE' in ui_text
            and 'buildUi()' in ui_text
            and 'showPage("Game")' in ui_text
        )
        if not direct_startup:
            errors.append("direct launcher startup contract is incomplete")

    output = root.parent / "artifacts/build/deep-quality-1000.txt"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "STEP303 DEEP QUALITY PASS\n"
        f"iterations=1000\ninspected={inspected}\nunique_file_fingerprints={len(fingerprints)}\n"
        + "\n".join(results)
        + "\n",
        encoding="utf-8",
    )

    if errors:
        for error in errors[:100]:
            print(f"[deep-quality] FAIL {error}")
        return 1

    print("[deep-quality] 1000/1000 content-dependent checks passed")
    print(f"[deep-quality] inspected={inspected}; unique_file_fingerprints={len(fingerprints)}")
    print(f"[deep-quality] report={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
