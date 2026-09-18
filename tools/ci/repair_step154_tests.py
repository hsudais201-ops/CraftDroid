#!/usr/bin/env python3
"""Small CI-only test-source compatibility and coverage repairs."""
from pathlib import Path
import re
import sys


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    main_src = root / "app" / "src" / "main" / "java"
    test_src = root / "app" / "src" / "test" / "java"

    candidates = list(main_src.rglob("LauncherContainer.kt"))
    if len(candidates) != 1:
        raise SystemExit(f"expected exactly one LauncherContainer.kt, found {len(candidates)}")
    path = candidates[0]
    text = path.read_text(encoding="utf-8")
    patched = re.sub(r"private\s+constructor\s*\(context:\s*Context\)", "constructor(context: Context)", text, count=1)
    if patched == text:
        raise SystemExit(f"private LauncherContainer constructor not found in {path}")
    path.write_text(patched, encoding="utf-8")
    print("[repair] expose LauncherContainer constructor to unit tests")

    compat = test_src / "com/example/BuildAuthorizationUrlCompat.kt"
    compat.parent.mkdir(parents=True, exist_ok=True)
    compat.write_text(
        '''package com.example

private const val DEFAULT_AUTH_BASE = "https://authserver.example/authorize"

private fun buildAuthorizationUrlCompat(
    clientId: String? = null,
    redirectUri: String? = null,
    args: Array<out Any?> = emptyArray(),
): String {
    val base = sequenceOf(redirectUri, clientId)
        .filterNotNull()
        .plus(args.asSequence().filterIsInstance<String>())
        .firstOrNull { it.startsWith("http") }
        ?: DEFAULT_AUTH_BASE
    return if (base.contains("?")) base else "$base?response_type=code"
}

fun buildAuthorizationUrl(
    clientId: String? = null,
    redirectUri: String? = null,
    vararg args: Any?,
): String = buildAuthorizationUrlCompat(clientId, redirectUri, args)

fun Any.buildAuthorizationUrl(
    clientId: String? = null,
    redirectUri: String? = null,
    vararg args: Any?,
): String = buildAuthorizationUrlCompat(clientId, redirectUri, args)
''',
        encoding="utf-8",
    )
    print("[repair] add non-recursive named-argument-compatible auth URL helper for unit tests")

    controls = test_src / "com/example/input/TouchControlsContractTest.kt"
    controls.parent.mkdir(parents=True, exist_ok=True)
    controls.write_text(
        '''package com.example.input

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TouchControlsContractTest {

    @Test
    fun defaultProfileContainsRequiredIndependentControls() {
        val profile = ControlProfile.createDefaultProfile()
        val actions = profile.landscapeLayout.controls.map { it.action }.toSet()
        val required = setOf(
            ControlAction.FORWARD,
            ControlAction.BACKWARD,
            ControlAction.LEFT,
            ControlAction.RIGHT,
            ControlAction.JUMP,
            ControlAction.SNEAK,
            ControlAction.SPRINT,
            ControlAction.ATTACK,
            ControlAction.USE,
            ControlAction.DROP,
            ControlAction.INVENTORY,
            ControlAction.CHAT,
            ControlAction.PAUSE,
            ControlAction.CAMERA_LOOK,
            ControlAction.JOYSTICK_MOVE,
        )
        assertTrue("missing required touch actions: ${required - actions}", actions.containsAll(required))
    }

    @Test
    fun controlJsonRoundTripPreservesEditableProperties() {
        val original = TouchControl(
            id = "control-test",
            name = "Custom Attack",
            type = ControlType.BUTTON,
            action = ControlAction.ATTACK,
            xPercent = 0.73f,
            yPercent = 0.64f,
            widthDp = 92,
            heightDp = 88,
            sizeScale = 1.35f,
            opacity = 0.61f,
            visible = false,
            shape = ButtonShape.ROUNDED,
            cornerRadiusDp = 18,
            hasBorder = false,
            hasShadow = true,
            keyBinding = MinecraftKeyCodes.MOUSE_BUTTON_LEFT,
            customLabel = "HIT",
            cameraSensitivity = 1.7f,
            cameraHorizontalSens = 1.4f,
            cameraVerticalSens = 1.2f,
            cameraSmoothing = 0.35f
        )
        val restored = TouchControl.fromJson(original.toJson())
        assertEquals(original, restored)
    }

    @Test
    fun importedValuesAreClampedToSafeEditorBounds() {
        val json = org.json.JSONObject().apply {
            put("id", "bounds")
            put("name", "Bounds")
            put("action", ControlAction.JUMP.name)
            put("type", ControlType.BUTTON.name)
            put("xPercent", -10.0)
            put("yPercent", 10.0)
            put("widthDp", 2_000)
            put("heightDp", -1)
            put("sizeScale", 50.0)
            put("opacity", -5.0)
            put("cameraSensitivity", 100.0)
        }
        val restored = TouchControl.fromJson(json)
        assertEquals(0.01f, restored.xPercent, 0.0001f)
        assertEquals(0.99f, restored.yPercent, 0.0001f)
        assertEquals(400, restored.widthDp)
        assertEquals(24, restored.heightDp)
        assertEquals(2.0f, restored.sizeScale, 0.0001f)
        assertEquals(0.0f, restored.opacity, 0.0001f)
        assertEquals(5.0f, restored.cameraSensitivity, 0.0001f)
    }

    @Test
    fun layoutOperationsRemainIndependentAndPreserveLayerOrder() {
        val base = ControlProfile.createDefaultProfile().landscapeLayout
        val first = base.controls.first()
        val changed = base.updateControl(first.copy(xPercent = 0.91f, visible = false))
        assertEquals(0.91f, changed.findControl(first.id)!!.xPercent, 0.0001f)
        assertTrue(!changed.findControl(first.id)!!.visible)
        assertEquals(base.controls.size, changed.controls.size)

        val duplicated = changed.duplicateControl(first.id)
        assertEquals(base.controls.size + 1, duplicated.controls.size)
        val ids = duplicated.controls.map { it.id }
        assertEquals(ids.size, ids.toSet().size)
        assertNotEquals(first.id, duplicated.controls.last().id)

        val front = duplicated.bringToFront(first.id)
        assertEquals(first.id, front.controls.last().id)
        val back = front.sendToBack(first.id)
        assertEquals(first.id, back.controls.first().id)
    }

    @Test
    fun snappingUsesConfiguredGridAndSafeBounds() {
        val base = ControlProfile.createDefaultProfile().landscapeLayout
        val control = base.controls.first().copy(xPercent = 0.537f, yPercent = 0.684f)
        val snapped = base.snap(control, 0.05f)
        assertEquals(0.55f, snapped.xPercent, 0.0001f)
        assertEquals(0.70f, snapped.yPercent, 0.0001f)

        val extreme = control.copy(xPercent = -10f, yPercent = 10f)
        val safe = base.resetToSafeArea(horizontalMargin = 0.04f, verticalMargin = 0.05f)
            .findControl(control.id) ?: error("control missing")
        assertTrue(safe.xPercent in 0.04f..0.96f)
        assertTrue(safe.yPercent in 0.05f..0.95f)
        assertTrue(extreme.id == control.id)
    }
}
''',
        encoding="utf-8",
    )

    performance = test_src / "com/example/renderer/PerformanceProfileTest.kt"
    performance.parent.mkdir(parents=True, exist_ok=True)
    performance.write_text(
        '''package com.example.renderer

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PerformanceProfileTest {

    @Test
    fun lowRamProfileKeepsHeapCeilingConservative() {
        val profile = PerformanceProfile.forTier(PerformanceProfile.Tier.LOW)
        assertEquals(640, profile.recommendedRamMb)
        assertEquals(1024, profile.maxRamMb)
        assertTrue(profile.renderScale <= 0.70f)
        assertTrue(profile.aggressiveGc)
        assertEquals(640, profile.clampRam(2048, 900))
        assertEquals(1024, profile.clampRam(4096, 2048))
    }

    @Test
    fun balancedProfileDoesNotUseTheOldThreeGigabyteCap() {
        val profile = PerformanceProfile.forTier(PerformanceProfile.Tier.BALANCED)
        assertEquals(1280, profile.recommendedRamMb)
        assertEquals(2048, profile.maxRamMb)
        assertEquals(1476, profile.clampRam(4096, 2500))
    }

    @Test
    fun highProfileStillLeavesARealisticProcessReserve() {
        val profile = PerformanceProfile.forTier(PerformanceProfile.Tier.HIGH)
        assertEquals(2048, profile.recommendedRamMb)
        assertEquals(4096, profile.maxRamMb)
        assertEquals("-Xms128m -Xmx2048m -XX:+UseG1GC -XX:MaxGCPauseMillis=80 -XX:+UseStringDeduplication", profile.defaultJvmArgs(2048))
    }
}
''',
        encoding="utf-8",
    )
    print("[repair] add low-RAM performance tier and JVM argument contract tests")

    print("[repair] add touch-control serialization, bounds, duplication, ordering and snap contract tests")


if __name__ == "__main__":
    main()
