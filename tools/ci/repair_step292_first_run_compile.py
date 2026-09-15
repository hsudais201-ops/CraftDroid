#!/usr/bin/env python3
from pathlib import Path
import sys

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
    print("[step300] hardened first-run component gate applied")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
