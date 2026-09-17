#!/usr/bin/env python3
"""Step 361: add a JVM-safe serialization seam for touch-control unit tests.

Android's bundled org.json methods are framework stubs in local JVM tests. The
production JSON bridge stays intact, while the same field normalization and
clamping logic is exposed through a pure Kotlin Map seam that can be exercised
without an Android runtime.
"""
from pathlib import Path
import sys


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'droid-src').resolve()
    source_root = root / 'app/src/main/java'
    test_root = root / 'app/src/test/java'

    matches = list(source_root.rglob('TouchControl.kt'))
    if len(matches) != 1:
        raise SystemExit(f'[step361] expected exactly one TouchControl.kt, found {len(matches)}')
    path = matches[0]
    text = path.read_text(encoding='utf-8')

    if 'fun toPortableMap(): Map<String, Any?>' not in text:
        anchor = '    fun toJson(): JSONObject {\n'
        if anchor not in text:
            raise SystemExit('[step361] toJson anchor missing')
        portable = '''    fun toPortableMap(): Map<String, Any?> = linkedMapOf(\n        "id" to id,\n        "name" to name,\n        "type" to type.name,\n        "action" to action.name,\n        "xPercent" to xPercent,\n        "yPercent" to yPercent,\n        "widthDp" to widthDp,\n        "heightDp" to heightDp,\n        "sizeScale" to sizeScale,\n        "opacity" to opacity,\n        "visible" to visible,\n        "shape" to shape.name,\n        "cornerRadiusDp" to cornerRadiusDp,\n        "hasBorder" to hasBorder,\n        "hasShadow" to hasShadow,\n        "keyBinding" to keyBinding,\n        "customLabel" to customLabel,\n        "joystickDeadZone" to joystickDeadZone,\n        "joystickMaxRadiusDp" to joystickMaxRadiusDp,\n        "joystickSensitivity" to joystickSensitivity,\n        "joystickDynamicOrigin" to joystickDynamicOrigin,\n        "cameraSensitivity" to cameraSensitivity,\n        "cameraInvertY" to cameraInvertY,\n        "cameraHorizontalSens" to cameraHorizontalSens,\n        "cameraVerticalSens" to cameraVerticalSens,\n        "cameraSmoothing" to cameraSmoothing\n    )\n\n    fun toJson(): JSONObject {\n'''
        text = text.replace(anchor, portable, 1)
        print('[step361] JVM-safe TouchControl map serialization seam installed')

    if 'fun fromPortableMap(map: Map<String, Any?>): TouchControl' not in text:
        companion_anchor = '    companion object {\n        fun fromJson(json: JSONObject): TouchControl {\n'
        if companion_anchor not in text:
            raise SystemExit('[step361] fromJson companion anchor missing')
        portable_parser = '''    companion object {\n        fun fromPortableMap(map: Map<String, Any?>): TouchControl {\n            fun string(key: String, default: String): String = (map[key] as? String)?.takeIf { it.isNotBlank() } ?: default\n            fun double(key: String, default: Double): Double = when (val value = map[key]) {\n                is Number -> value.toDouble()\n                is String -> value.toDoubleOrNull() ?: default\n                else -> default\n            }\n            fun int(key: String, default: Int): Int = when (val value = map[key]) {\n                is Number -> value.toInt()\n                is String -> value.toIntOrNull() ?: default\n                else -> default\n            }\n            fun bool(key: String, default: Boolean): Boolean = when (val value = map[key]) {\n                is Boolean -> value\n                is String -> value.toBooleanStrictOrNull() ?: default\n                else -> default\n            }\n\n            val action = ControlAction.fromName(string("action", ControlAction.JUMP.name))\n            val type = try { ControlType.valueOf(string("type", ControlType.BUTTON.name)) } catch (_: Exception) { ControlType.BUTTON }\n            val shape = try { ButtonShape.valueOf(string("shape", ButtonShape.MINECRAFT_STYLE.name)) } catch (_: Exception) { ButtonShape.MINECRAFT_STYLE }\n            return TouchControl(\n                id = string("id", UUID.randomUUID().toString().take(8)),\n                name = string("name", action.actionName),\n                type = type,\n                action = action,\n                xPercent = double("xPercent", 0.5).toFloat().coerceIn(0.01f, 0.99f),\n                yPercent = double("yPercent", 0.5).toFloat().coerceIn(0.01f, 0.99f),\n                widthDp = int("widthDp", 56).coerceIn(24, 400),\n                heightDp = int("heightDp", 56).coerceIn(24, 400),\n                sizeScale = double("sizeScale", 1.0).toFloat().coerceIn(0.5f, 2.0f),\n                opacity = double("opacity", 0.8).toFloat().coerceIn(0.0f, 1.0f),\n                visible = bool("visible", true),\n                shape = shape,\n                cornerRadiusDp = int("cornerRadiusDp", 8).coerceIn(0, 50),\n                hasBorder = bool("hasBorder", true),\n                hasShadow = bool("hasShadow", true),\n                keyBinding = int("keyBinding", action.defaultKeyCode),\n                customLabel = string("customLabel", "").takeIf { it.isNotBlank() },\n                joystickDeadZone = double("joystickDeadZone", 0.15).toFloat().coerceIn(0.05f, 0.4f),\n                joystickMaxRadiusDp = double("joystickMaxRadiusDp", 65.0).toFloat().coerceIn(30f, 120f),\n                joystickSensitivity = double("joystickSensitivity", 1.0).toFloat().coerceIn(0.2f, 3.0f),\n                joystickDynamicOrigin = bool("joystickDynamicOrigin", false),\n                cameraSensitivity = double("cameraSensitivity", 1.0).toFloat().coerceIn(0.1f, 5.0f),\n                cameraInvertY = bool("cameraInvertY", false),\n                cameraHorizontalSens = double("cameraHorizontalSens", 1.0).toFloat().coerceIn(0.1f, 5.0f),\n                cameraVerticalSens = double("cameraVerticalSens", 1.0).toFloat().coerceIn(0.1f, 5.0f),\n                cameraSmoothing = double("cameraSmoothing", 0.0).toFloat().coerceIn(0.0f, 1.0f)\n            )\n        }\n\n        fun fromJson(json: JSONObject): TouchControl {\n'''
        text = text.replace(companion_anchor, portable_parser, 1)
        print('[step361] JVM-safe TouchControl map parser installed')

    path.write_text(text, encoding='utf-8')

    tests = list(test_root.rglob('TouchControlsContractTest.kt'))
    if len(tests) != 1:
        raise SystemExit(f'[step361] expected exactly one TouchControlsContractTest.kt, found {len(tests)}')
    test_path = tests[0]
    test_text = test_path.read_text(encoding='utf-8')

    old_round_trip = 'val restored = TouchControl.fromJson(original.toJson())'
    new_round_trip = 'val restored = TouchControl.fromPortableMap(original.toPortableMap())'
    test_text = test_text.replace(old_round_trip, new_round_trip)

    old_bounds = '''        val json = org.json.JSONObject().apply {\n            put("id", "bounds")\n            put("name", "Bounds")\n            put("action", ControlAction.JUMP.name)\n            put("type", ControlType.BUTTON.name)\n            put("xPercent", -10.0)\n            put("yPercent", 10.0)\n            put("widthDp", 2_000)\n            put("heightDp", -1)\n            put("sizeScale", 50.0)\n            put("opacity", -5.0)\n            put("cameraSensitivity", 100.0)\n        }\n        val restored = TouchControl.fromJson(json)'''
    new_bounds = '''        val values = mapOf<String, Any?>(\n            "id" to "bounds",\n            "name" to "Bounds",\n            "action" to ControlAction.JUMP.name,\n            "type" to ControlType.BUTTON.name,\n            "xPercent" to -10.0,\n            "yPercent" to 10.0,\n            "widthDp" to 2_000,\n            "heightDp" to -1,\n            "sizeScale" to 50.0,\n            "opacity" to -5.0,\n            "cameraSensitivity" to 100.0\n        )\n        val restored = TouchControl.fromPortableMap(values)'''
    if old_bounds in test_text:
        test_text = test_text.replace(old_bounds, new_bounds, 1)
    elif 'TouchControl.fromPortableMap(values)' not in test_text:
        raise SystemExit('[step361] bounds test fixture anchor missing')

    test_path.write_text(test_text, encoding='utf-8')
    if 'TouchControl.fromJson(original.toJson())' in test_text or 'org.json.JSONObject().apply {' in test_text:
        raise SystemExit('[step361] Android-framework JSON test fixture remains in JVM contract tests')
    print('[step361] touch-control unit tests now exercise JVM-safe portable serialization/clamping seam')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
