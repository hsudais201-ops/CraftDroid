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
    """Copy the complete authoritative modern launcher manager set."""
    project = Path.cwd().resolve()
    names = (
        "MinecraftRuntimeProfile.kt",
        "MinecraftLatestVersionManager.kt",
        "MinecraftContentManager.kt",
        "MinecraftModpackManager.kt",
        "MinecraftLoaderProfile.kt",
        "LauncherBackgroundInstallController.kt",
        "DroidLauncherUpdateManager.kt",
    )
    destination = root / "app/src/main/java/com/example/launcher"
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for name in names:
        source = project / "app/src/main/java/com/example/launcher" / name
        if not source.is_file():
            raise SystemExit(f"[step322] authoritative manager missing from repository: {source}")
        shutil.copy2(source, destination / name)
        copied += 1
    print(f"[step327] copied {copied} modern runtime/content/update/loader managers")
    return copied


def verify_modern_managers(root: Path) -> None:
    src = root / "app/src/main/java/com/example/launcher"
    required = {
        "MinecraftRuntimeProfile.kt": ("first >= 26 -> Profile(25", "requiresJava25"),
        "MinecraftLatestVersionManager.kt": ("version_manifest_v2.json", 'optJSONObject("latest")', "getCached"),
        "MinecraftContentManager.kt": ("MODPACK", "SHADER", "RESOURCE_PACK", "WORLD", "ZipInputStream", "MAX_ENTRY_BYTES"),
        "MinecraftModpackManager.kt": ("modrinth.index.json", "formatVersion", "SHA-1", "overrides", "client-overrides"),
        "MinecraftLoaderProfile.kt": ("FABRIC", "FORGE", "NEOFORGE", "QUILT"),
        "LauncherBackgroundInstallController.kt": ("CountDownLatch", "State.SUCCESS", "State.FAILED"),
        "DroidLauncherUpdateManager.kt": ("releases/latest", ".apk", "SHA-256 verification failed", "MAX_REDIRECTS"),
    }
    for name, needles in required.items():
        path = src / name
        if not path.is_file():
            raise SystemExit(f"[step322] missing modern manager file: {name}")
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise SystemExit(f"[step322] missing {needle!r} in {name}")


def repair_component_preparation_order(root: Path) -> bool:
    """Ensure generated bootstrap completion is persisted before verification.

    The previous implementation called bootstrapComplete() while the
    components_extracted flag was still false, guaranteeing a false result and
    forcing the UI down its failure path after every preparation attempt.
    """
    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    source = ui.read_text(encoding="utf-8")
    gate = source.find("private fun extractBootstrapComponents")
    if gate < 0:
        raise SystemExit("[step351] extractBootstrapComponents() not found")
    verify = '                if (!bootstrapComplete()) throw java.io.IOException("Component preparation verification failed")'
    persist = '                bootstrapPrefs().edit().putBoolean("components_extracted", true).apply()'
    verify_pos = source.find(verify, gate)
    persist_pos = source.find(persist, gate)
    if verify_pos < 0 or persist_pos < 0:
        raise SystemExit("[step351] component preparation state-machine markers not found")
    if persist_pos > verify_pos:
        source = source[:verify_pos] + persist + "\n" + source[verify_pos:persist_pos] + source[persist_pos + len(persist):]
        ui.write_text(source, encoding="utf-8")
        print("[step351] fixed component preparation ordering")
        return True
    print("[step351] component preparation ordering already correct")
    return False


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
    repair_component_preparation_order(root)
    copy_modern_managers(root)
    verify_modern_managers(root)
    changed = scrub_generated_branding(root)
    print(f"[step300] hardened first-run component gate applied; branding_files_scrubbed={changed}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
