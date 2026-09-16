#!/usr/bin/env python3
"""Step 348: harden actions on the screenshot-matched Version / Instances UI."""
from pathlib import Path
import sys
MARKER = "// STEP348_VERSION_INSTANCE_ACTIONS"
def main() -> int:
    root=Path(sys.argv[1] if len(sys.argv)>1 else 'droid-src').resolve()
    ui=root/'app/src/main/java/com/example/launcher/DroidLauncherUiActivity.kt'
    if not ui.is_file(): raise SystemExit(f'[step348] missing UI: {ui}')
    s=ui.read_text(encoding='utf-8')
    if MARKER in s: return 0
    anchor='    private fun showVersionInstancesPage() {'
    if anchor not in s: raise SystemExit('[step348] page missing')
    s=s.replace(anchor,anchor+'\n        '+MARKER,1)
    s=s.replace('setOnClickListener { field.text.clear() }','setOnClickListener { listFrame.removeView(row); listFrame.requestLayout() }',1)
    s=s.replace('setOnClickListener { android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Folder: ${field.text}", android.widget.Toast.LENGTH_SHORT).show() }','setOnClickListener { startActivity(android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT_TREE)) }',1)
    s=s.replace('dashedBorderPanel("Create server", 54) { android.widget.Toast.makeText(this@DroidLauncherUiActivity, "Create server", android.widget.Toast.LENGTH_SHORT).show() }','dashedBorderPanel("Create server", 54) { showServerDialog(-1) }',1)
    s=s.replace('else -> android.widget.Toast.makeText(this@DroidLauncherUiActivity, pair.second, android.widget.Toast.LENGTH_SHORT).show()','else -> if (pair.second == "Files") startActivity(android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT_TREE)) else startActivity(android.content.Intent(android.content.Intent.ACTION_OPEN_DOCUMENT).setType("*/*").addCategory(android.content.Intent.CATEGORY_OPENABLE))',1)
    ui.write_text(s,encoding='utf-8')
    print('[step348] Version / Instances actions hardened')
    return 0
if __name__=='__main__': raise SystemExit(main())
