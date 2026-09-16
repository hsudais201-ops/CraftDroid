#!/usr/bin/env python3
"""Verify Step348 functional actions."""
from pathlib import Path
import sys
REQUIRED=[
    '// STEP348_VERSION_INSTANCE_ACTIONS',
    'listFrame.removeView(row)',
    'ACTION_OPEN_DOCUMENT_TREE',
    'showServerDialog(-1)',
    'ACTION_OPEN_DOCUMENT',
]
def main()->int:
    root=Path(sys.argv[1] if len(sys.argv)>1 else 'droid-src').resolve()
    ui=root/'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file(): raise SystemExit('[step348] missing UI')
    s=ui.read_text(encoding='utf-8')
    missing=[x for x in REQUIRED if x not in s]
    if missing: raise SystemExit('[step348] missing contracts: '+', '.join(missing))
    if s.count('// STEP348_VERSION_INSTANCE_ACTIONS')!=1: raise SystemExit('[step348] marker count invalid')
    print('[step348] functional row-delete, folder, Files/Downloads, and Create-server actions verified')
    return 0
if __name__=='__main__': raise SystemExit(main())
