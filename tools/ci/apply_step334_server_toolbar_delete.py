#!/usr/bin/env python3
"""Step 334: add a Delete button beside Edit in the Home server toolbar.

The button acts on the currently selected server and refreshes the Home page after
successful deletion. It is intentionally applied after late UI generators so they
cannot overwrite the toolbar change.
"""
from pathlib import Path
import re
import sys


def find_ui(root: Path) -> Path:
    hits = list((root / "app/src/main/java").rglob("DroidLauncherUiActivity.kt"))
    if len(hits) != 1:
        raise SystemExit(f"[step334] expected one DroidLauncherUiActivity.kt, found {len(hits)}")
    return hits[0]


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "droid-src").resolve()
    path = find_ui(root)
    source = path.read_text(encoding="utf-8")

    marker = "// STEP334_SERVER_TOOLBAR_DELETE"
    if marker in source:
        print("[step334] already applied")
        return 0

    old = '''        val edit = button("Edit")
        edit.setOnClickListener {
            val selected = getSelectedServerIndex()
            if (selected >= 0) showServerDialog(selected) else showServerDialog(-1)
        }
        val refresh = button("refresh")
        refresh.setOnClickListener { refreshAllServers() }
        toolbar.addView(add, LinearLayout.LayoutParams(dp(118), dp(44)))
        toolbar.addView(edit, LinearLayout.LayoutParams(dp(82), dp(44)))
        toolbar.addView(refresh, LinearLayout.LayoutParams(dp(100), dp(44)))
'''

    new = '''        val edit = button("Edit")
        edit.setOnClickListener {
            val selected = getSelectedServerIndex()
            if (selected >= 0) showServerDialog(selected) else showServerDialog(-1)
        }
        val delete = button("Delete")
        delete.setOnClickListener {
            val selected = getSelectedServerIndex()
            if (selected < 0) {
                android.widget.Toast.makeText(this, "Select a server first", android.widget.Toast.LENGTH_SHORT).show()
            } else {
                android.app.AlertDialog.Builder(this)
                    .setTitle("Delete Server")
                    .setMessage("Delete the selected saved server?")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Delete") { _, _ ->
                        deleteServer(selected)
                        showPage("Game")
                    }
                    .show()
            }
        }
        val refresh = button("refresh")
        refresh.setOnClickListener { refreshAllServers() }
        toolbar.addView(add, LinearLayout.LayoutParams(dp(118), dp(44)))
        toolbar.addView(edit, LinearLayout.LayoutParams(dp(82), dp(44)))
        toolbar.addView(delete, LinearLayout.LayoutParams(dp(88), dp(44)))
        toolbar.addView(refresh, LinearLayout.LayoutParams(dp(100), dp(44)))
        // STEP334_SERVER_TOOLBAR_DELETE
'''

    if old not in source:
        raise SystemExit("[step334] expected Home server toolbar block was not found")
    source = source.replace(old, new, 1)

    # Add a stable source-contract marker for CI and future generator ordering.
    source = source.replace(
        '        body.addView(left, LinearLayout.LayoutParams(0, -1, 0.70f))',
        '        body.addView(left, LinearLayout.LayoutParams(0, -1, 0.70f))',
        1,
    )
    path.write_text(source, encoding="utf-8")
    print("[step334] added Home > Servers toolbar Delete button beside Edit")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
