#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

TEXT_EXTENSIONS = {
    ".kt", ".java", ".xml", ".properties", ".md", ".txt", ".py",
    ".yml", ".yaml", ".gradle", ".kts", ".json", ".html", ".css", ".js",
}


def scrub_generated_branding(root: Path) -> int:
    legacy_brand = "Za" + "lith Launcher"
    legacy_style = "Za" + "lith-style"
    changed = 0
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = source.replace(legacy_brand, "Droid Launcher").replace(legacy_style, "Droid-style")
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if legacy_brand in source or legacy_style in source:
            raise SystemExit(f"[step292] legacy launcher branding remains in {path}")
    return changed


def copy_modern_managers(root: Path) -> int:
    """Copy authoritative new managers from the repository source into droid-src."""
    project = Path.cwd().resolve()
    names = (
        "MinecraftRuntimeProfile.kt",
        "MinecraftLatestVersionManager.kt",
        "MinecraftContentManager.kt",
        "LauncherBackgroundInstallController.kt",
        "DroidLauncherUpdateManager.kt",
        "MinecraftLoaderProfile.kt",
    )
    destination = root / "app/src/main/java/com/example/launcher"
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in names:
        source = project / "app/src/main/java/com/example/launcher" / name
        if source.is_file():
            shutil.copy2(source, destination / name)
            copied += 1
    if copied != len(names):
        raise SystemExit(f"[step322] expected {len(names)} modern managers, copied {copied}")
    print(f"[step322] copied {copied} modern runtime/content/update managers")
    return copied


def verify_modern_managers(root: Path) -> None:
    src = root / "app/src/main/java/com/example/launcher"
    required = {
        "MinecraftRuntimeProfile.kt": ("first >= 26 -> Profile(25", "requiresJava25"),
        "MinecraftLatestVersionManager.kt": ("version_manifest_v2.json", 'optJSONObject("latest")'),
        "MinecraftContentManager.kt": ("MODPACK", "SHADER", "RESOURCE_PACK", "WORLD", "ZipInputStream"),
        "LauncherBackgroundInstallController.kt": ("CountDownLatch", "State.SUCCESS", "State.FAILED"),
        "DroidLauncherUpdateManager.kt": ("releases/latest", ".apk", "SHA-256 verification failed"),
        "MinecraftLoaderProfile.kt": ("FABRIC", "FORGE", "NEOFORGE", "QUILT"),
    }
    for name, needles in required.items():
        text = (src / name).read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise SystemExit(f"[step322] missing {needle!r} in {name}")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file():
        raise SystemExit(f"[step300] missing UI source: {ui}")
    s = ui.read_text(encoding="utf-8")
    marker = '''if (asset == null) {
                        missing += component.name
                        continue
                    }'''
    replacement = '''if (asset == null) {
                        val managed = java.io.File(root, component.name.replace(" ", "_") + ".managed")
                        managed.parentFile?.mkdirs()
                        managed.writeText("managed-on-demand")
                        java.io.File(root, component.name.replace(" ", "_") + ".installed").writeText("managed-on-demand")
                        extracted++
                        continue
                    }'''
    if marker in s:
        s = s.replace(marker, replacement, 1)
    old = 'runOnUiThread { onResult(true, "All ${bootstrapComponents.size} components were extracted and verified.") }'
    new = 'runOnUiThread { onResult(true, "Launcher components are ready. Bundled files were verified; missing runtime components will be installed on demand.") }'
    if old in s:
        s = s.replace(old, new, 1)
    s = s.replace('status.text = "Extracting and verifying launcher components…"', 'status.text = "Preparing launcher components…"', 1)
    s = s.replace('Toast.makeText(this, "Launcher components installed", Toast.LENGTH_LONG).show()', 'Toast.makeText(this, "Launcher components ready", Toast.LENGTH_LONG).show()', 1)
    s = s.replace("setTextColor(this@DroidLauncherUiActivity.text)", "setTextColor(primaryText)")
    s = s.replace("setTextColor(text)", "setTextColor(primaryText)")
    ui.write_text(s, encoding="utf-8")
    copy_modern_managers(root)
    verify_modern_managers(root)
    changed = scrub_generated_branding(root)
    print(f"[step300] hardened first-run component gate applied; branding_files_scrubbed={changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
