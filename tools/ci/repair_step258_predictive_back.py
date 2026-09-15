#!/usr/bin/env python3
"""Migrate the generated GameActivity away from deprecated onBackPressed()."""
from pathlib import Path
import re
import sys

NEW_BACK = '''    private fun handleSystemBack() {
        touchOverlay.releaseAllTouches()
        container.launchManager.kill()
        finish()
    }

    private val predictiveBackCallback = if (android.os.Build.VERSION.SDK_INT >= 33) {
        object : android.window.OnBackInvokedCallback {
            override fun onBackInvoked() {
                handleSystemBack()
            }
        }
    } else null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        window.setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN)

        input = container.touchInputManager.inputBridge
        gameView = GameSurfaceView(this, input, this, container.touchInputManager)
        touchOverlay = TouchControlsOverlayView(this, container.touchInputManager)

        val root = FrameLayout(this).apply {
            isFocusable = true
            isFocusableInTouchMode = true
            addView(gameView, FrameLayout.LayoutParams(-1, -1))
            addView(touchOverlay, FrameLayout.LayoutParams(-1, -1))
        }
        setContentView(root)
        root.requestFocus()
        touchOverlay.requestApplyInsets()
        updateControlOrientation(resources.configuration.orientation)
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            onBackInvokedDispatcher.registerOnBackInvokedCallback(
                android.window.OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                predictiveBackCallback!!
            )
        }
        LauncherLogger.info("GameActivity created with Minecraft surface + runtime touch overlay")
    }
'''


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd().resolve()
    path = root / "app/src/main/java/com/example/game/GameActivity.kt"
    if not path.is_file():
        raise SystemExit(f"[step258] GameActivity not found: {path}")
    source = path.read_text(encoding="utf-8")
    if "override fun onBackPressed()" not in source:
        print("[step258] GameActivity already migrated")
        return 0

    source = source.replace("import android.view.Surface\n", "import android.view.Surface\nimport android.view.KeyEvent\n")
    source = source.replace("import android.widget.FrameLayout\n", "import android.widget.FrameLayout\n")

    old_oncreate = re.search(r"    override fun onCreate\(savedInstanceState: Bundle\?\) \{[\s\S]*?\n    \}\n\n    override fun onSurfaceReady", source)
    if not old_oncreate:
        raise SystemExit("[step258] onCreate anchor not found")
    oncreate = NEW_BACK.rstrip() + "\n\n    override fun onSurfaceReady"
    source = source[:old_oncreate.start()] + oncreate + source[old_oncreate.end():]

    old_back = re.search(r"    override fun onBackPressed\(\) \{[\s\S]*?\n    \}\n", source)
    if not old_back:
        raise SystemExit("[step258] onBackPressed block not found after onCreate patch")
    replacement = '''    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && android.os.Build.VERSION.SDK_INT < 33) {
            handleSystemBack()
            return true
        }
        return super.onKeyUp(keyCode, event)
    }

    override fun onDestroy() {
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            predictiveBackCallback?.let { onBackInvokedDispatcher.unregisterOnBackInvokedCallback(it) }
        }
        touchOverlay.releaseAllTouches()
        super.onDestroy()
    }
'''
    source = source[:old_back.start()] + replacement + source[old_back.end():]
    path.write_text(source, encoding="utf-8")
    if "override fun onBackPressed()" in source:
        raise SystemExit("[step258] deprecated onBackPressed override remains")
    if "OnBackInvokedCallback" not in source:
        raise SystemExit("[step258] predictive back callback was not installed")
    print(f"[step258] migrated predictive back handling: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
