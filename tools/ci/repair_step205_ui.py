#!/usr/bin/env python3
from pathlib import Path
import re
import sys


def manifest_path(root: Path) -> Path:
    matches = list(root.glob("**/src/main/AndroidManifest.xml"))
    if not matches:
        raise SystemExit(f"[step205-repair] no manifest under {root}")
    return matches[0]


def launcher_class(manifest: str) -> str:
    pattern = r'<(?:activity|activity-alias)[ \t\r\n][\s\S]*?</(?:activity|activity-alias)>'
    for block in re.findall(pattern, manifest):
        if "android.intent.action.MAIN" not in block or "android.intent.category.LAUNCHER" not in block:
            continue
        match = re.search(r'android:name="([^"]+)"', block)
        if match:
            name = match.group(1)
            if name.startswith("."):
                pkg = re.search(r'android:package="([^"]+)"', manifest)
                if pkg:
                    name = pkg.group(1) + name
            return name
    return ""


def remove_old_launcher_filters(manifest: str) -> str:
    pattern = r'<(?:activity|activity-alias)[ \t\r\n][\s\S]*?</(?:activity|activity-alias)>'

    def patch(block: str) -> str:
        if "DroidLauncherUiActivity" in block:
            return block
        if "android.intent.action.MAIN" not in block or "android.intent.category.LAUNCHER" not in block:
            return block
        def remove_filter(m: re.Match) -> str:
            body = m.group(0)
            if "android.intent.action.MAIN" in body and "android.intent.category.LAUNCHER" in body:
                return ""
            return body
        return re.sub(r'<intent-filter>[\s\S]*?</intent-filter>', remove_filter, block, count=1)

    return re.sub(pattern, patch, manifest)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    manifest = manifest_path(root)
    manifest_text = manifest.read_text(encoding="utf-8")
    existing = launcher_class(manifest_text)

    ui = root / "app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.exists():
        raise SystemExit(f"[step205-repair] missing generated UI: {ui}")
    source = ui.read_text(encoding="utf-8")
    source = source.replace("setTextColor(text)", "setTextColor(primaryText)")
    source = source.replace("if (filled) Color.WHITE else text", "if (filled) Color.WHITE else primaryText")
    source = source.replace("private val text = Color.rgb(31, 37, 44)", "private val primaryText = Color.rgb(31, 37, 44)")
    source = source.replace(
        '''        val parts = component.split('/', limit = 2)\n        if (parts.size == 2) {\n            try {\n                val i = Intent().setClassName(packageName, parts[1].removePrefix("."))\n                startActivity(i)\n            } catch (_: Exception) {\n                // The UI remains usable even when the legacy activity is unavailable.\n            }\n        }''',
        '''        if (component.isNotBlank()) {\n            try {\n                val i = Intent().setClassName(packageName, component)\n                startActivity(i)\n            } catch (_: Exception) {\n                // The UI remains usable even when the legacy activity is unavailable.\n            }\n        }'''
    )
    if existing:
        source = source.replace('private const val EXISTING_LAUNCHER_COMPONENT = "__EXISTING_LAUNCHER_COMPONENT__"', f'private const val EXISTING_LAUNCHER_COMPONENT = "{existing}"')
    ui.write_text(source, encoding="utf-8")
    manifest.write_text(remove_old_launcher_filters(manifest_text), encoding="utf-8")
    print(f"[step205-repair] launcher component={existing or 'none detected'}")
    print("[step205-repair] UI source and launcher intent wiring hardened")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
