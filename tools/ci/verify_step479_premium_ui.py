#!/usr/bin/env python3
"""Verify Step479 premium UI contracts."""
from pathlib import Path
import sys

def main():
    root=Path(sys.argv[1] if len(sys.argv)>1 else "droid-src").resolve()
    ui=root/"app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt"
    if not ui.is_file(): raise SystemExit("[step479-verify] UI missing")
    s=ui.read_text(encoding="utf-8")
    required=(
        "// STEP479_PREMIUM_UI",
        "INSTALL & CONTINUE",
        '"Mod"->step479Manager("Mod")',
        '"Modpack"->step479Manager("Modpack")',
        '"Shader Pack","Shaders"->step479Manager("Shader Pack")',
        '"Resource Pack","Resource Packs"->step479Manager("Resource Pack")',
        '"World","Worlds"->step479Manager("World")',
        '"Versions"->step479Versions()',
        '"Servers"->step479Servers()',
        "MinecraftVersionInstallManager.isInstalled",
        "installMinecraftVersion(version)",
        "showServerDialog(-1)",
        "refreshServerStatus(it.first,it.second)",
        "step391StartContentImport(type)",
        "step376PrepareFirstRun",
        '"26.3"','"26.2"','"26.1.2"','"26.1.1"'
    )
    missing=[x for x in required if x not in s]
    if missing: raise SystemExit("[step479-verify] missing: "+", ".join(missing))
    if s.count("private fun step479Versions()")!=1 or s.count("private fun step479Servers()")!=1:
        raise SystemExit("[step479-verify] duplicate premium pages")
    if 'if(step375Prefs().getBoolean("installed",false)) showPage("Home") else showPage("FirstRun")' not in s:
        raise SystemExit("[step479-verify] first-run gate missing")
    print("[step479-verify] premium UI, first-run install, content managers, version install and server manager PASS")

if __name__=="__main__": main()
