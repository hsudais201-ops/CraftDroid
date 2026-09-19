package com.example.game

import android.app.Activity
import android.os.Bundle
import android.content.res.Configuration
import android.view.Surface
import android.view.WindowManager
import android.widget.FrameLayout
import com.example.core.LauncherContainer
import com.example.input.InputBridge
import com.example.logs.LauncherLogger

/** Full-screen host for Minecraft with a real rendering surface and runtime touch overlay. */
class GameActivity : Activity(), GameSurfaceView.Callbacks {
    private val container by lazy { LauncherContainer.get(applicationContext) }
    private lateinit var input: InputBridge
    private lateinit var gameView: GameSurfaceView
    private lateinit var touchOverlay: TouchControlsOverlayView

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
        LauncherLogger.info("GameActivity created with Minecraft surface + runtime touch overlay")
    }

    override fun onSurfaceReady(surface: Surface, width: Int, height: Int) {
        // Surface lifecycle ownership is centralized in MinecraftLaunchManager.
        // Calling NativeGameBridge directly here as well would apply the same
        // Surface twice, recreate EGL/GLFW state twice, and increment the native
        // surface generation twice.
        container.launchManager.onGameSurfaceReady(surface, width, height)
    }

    override fun onSurfaceDestroyed() {
        touchOverlay.releaseAllTouches()
        // MinecraftLaunchManager owns the native surface teardown/defer logic.
        container.launchManager.onGameSurfaceDestroyed()
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        updateControlOrientation(newConfig.orientation)
        touchOverlay.requestApplyInsets()
        touchOverlay.releaseAllTouches()
        LauncherLogger.info("GameActivity configuration changed: orientation=${newConfig.orientation}")
    }

    private fun updateControlOrientation(orientation: Int) {
        container.touchInputManager.setOrientation(
            if (orientation == Configuration.ORIENTATION_LANDSCAPE) {
                com.example.input.LayoutOrientation.LANDSCAPE
            } else {
                com.example.input.LayoutOrientation.PORTRAIT
            }
        )
    }

    override fun onBackPressed() {
        touchOverlay.releaseAllTouches()
        container.launchManager.kill()
        super.onBackPressed()
    }
}
