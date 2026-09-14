#!/usr/bin/env python3
from pathlib import Path
import re
import sys


def find_manifest(root: Path) -> Path:
    matches = list(root.glob("**/src/main/AndroidManifest.xml"))
    if not matches:
        raise SystemExit(f"[step205-repair] no manifest under {root}")
    return matches[0]


def find_existing_launcher(manifest: str) -> str:
    pattern = r'<(?:activity|activity-alias)[ \t\r\n][\s\S]*?</(?:activity|activity-alias)>'
    for block in re.findall(pattern, manifest):
        if "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            match = re.search(r'android:name="([^"]+)"', block)
            if match:
                return match.group(1)
    # Also tolerate self-closing launcher declarations in hand-edited manifests.
    for block in re.findall(r'<(?:activity|activity-alias)\b[^>]*?/\s*>', manifest):
        if "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            match = re.search(r'android:name="([^"]+)"', block)
            if match:
                return match.group(1)
    return ""


def remove_old_launcher_filters(manifest: str) -> str:
    pattern = r'<(?:activity|activity-alias)[ \t\r\n][\s\S]*?</(?:activity|activity-alias)>'

    def patch(block: str) -> str:
        if "DroidLauncherUiActivity" not in block and "android.intent.action.MAIN" in block and "android.intent.category.LAUNCHER" in block:
            block = re.sub(r'<intent-filter>[\s\S]*?</intent-filter>', lambda m: "" if ("android.intent.action.MAIN" in m.group(0) and "android.intent.category.LAUNCHER" in m.group(0)) else m.group(0), block)
        return block

    return re.sub(pattern, patch, manifest)


def repair_launch_method(source: str) -> str:
    start = source.find("    private fun launchExistingActivity()")
    companion = source.find("    companion object", start if start >= 0 else 0)
    if start < 0 or companion < 0:
        raise SystemExit("[step205-repair] launchExistingActivity/companion anchors not found")
    launch_body = '''    private fun launchExistingActivity() {
        val component = EXISTING_LAUNCHER_COMPONENT
        if (component.isNotBlank()) {
            try {
                startActivity(Intent().setClassName(packageName, component))
            } catch (_: Exception) {
                // Keep the launcher UI usable when the legacy activity is unavailable.
            }
        }
    }

'''
    return source[:start] + launch_body + source[companion:]


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    manifest = find_manifest(root)
    manifest_text = manifest.read_text(encoding="utf-8")
    existing = find_existing_launcher(manifest_text)

    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step205-repair] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    source = source.replace("setTextColor(text)", "setTextColor(primaryText)")
    source = source.replace("if (filled) Color.WHITE else text", "if (filled) Color.WHITE else primaryText")
    source = source.replace("private val text = Color.rgb(31, 37, 44)", "private val primaryText = Color.rgb(31, 37, 44)")
    source = repair_launch_method(source)
    if existing:
        source = re.sub(r'private const val EXISTING_LAUNCHER_COMPONENT = "[^"]*"', f'private const val EXISTING_LAUNCHER_COMPONENT = "{existing}"', source)
    ui.write_text(source, encoding="utf-8")
    manifest.write_text(remove_old_launcher_filters(manifest_text), encoding="utf-8")
    print(f"[step205-repair] existing launcher={existing or 'none'}")
    print("[step205-repair] UI colors, launch wiring, and duplicate launcher filters fixed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
