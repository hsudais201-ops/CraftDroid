#!/usr/bin/env python3
"""Deterministic source repairs for the Step 153 CraftDroid archive.

The uploaded source ZIP is kept intact; CI applies these source-level fixes
immediately after extraction so the original archive remains reproducible.
"""
from pathlib import Path
import sys


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly 1 match in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[repair] {label}")


def replace_all(path: Path, old: str, new: str, label: str, minimum: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count < minimum:
        raise SystemExit(f"{label}: expected at least {minimum} matches in {path}, found {count}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[repair] {label}: {count} replacements")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "craftdroid-src").resolve()
    src = root / "app" / "src" / "main" / "java"
    if not src.is_dir():
        raise SystemExit(f"Android source directory not found: {src}")

    game_surface = src / "com/example/game/GameSurfaceView.kt"
    replace_once(
        game_surface,
        '            NativeGameBridge.sendChar(event.unicodeChar)\n',
        '            // Text/character input is handled by the normal Android key event path.\n',
        "remove nonexistent NativeGameBridge.sendChar call",
    )

    native_bridge = src / "com/example/game/NativeGameBridge.kt"
    replace_once(
        native_bridge,
        '    fun javaState(): Int = loaded && runCatching { nativeGetJavaState() }.getOrDefault(0)\n',
        '    fun javaState(): Int = if (!loaded) 0 else runCatching { nativeGetJavaState() }.getOrDefault(0)\n',
        "fix javaState Boolean/Int expression",
    )

    touch = src / "com/example/game/TouchControlsOverlayView.kt"
    marker = '    private fun releasePointer(pointerId: Int, x: Float, y: Float) {\n'
    text = touch.read_text(encoding="utf-8")
    if '    private fun releaseAllPointers()' not in text:
        if text.count(marker) != 1:
            raise SystemExit(f"releasePointer marker not found uniquely in {touch}")
        text = text.replace(marker, '    private fun releaseAllPointers() {\n        activePointers.keys.toList().forEach { id -> releasePointer(id, 0f, 0f) }\n        activePointers.clear()\n        controlPointerTokens.clear()\n        cameraLastPositions.clear()\n        joystickPointerId = null\n        joystickOriginX = 0f\n        joystickOriginY = 0f\n        touchManager.releaseAllInputs()\n    }\n\n' + marker)
        touch.write_text(text, encoding="utf-8")
        print("[repair] add releaseAllPointers cancellation helper")

    manager = src / "com/example/launcher/MinecraftLaunchManager.kt"
    replace_once(
        manager,
        '                val preferLwjgl3 = lwjglProfile.apiFamily == com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL3_NATIVE_GLFW\n',
        '                val preferLwjgl3 = lwjglProfile.family == com.example.renderer.LwjglRuntimeProfile.ApiFamily.LWJGL3_NATIVE_GLFW\n',
        "use existing LwjglRuntimeProfile.family property",
    )

    forge = src / "com/example/minecraft/ForgeNeoForgeInstaller.kt"
    replace_all(
        forge,
        '    V1, V2, LEGACY_PROFILE, UNSUPPORTED\n',
        '    V1, V2, LEGACY_PROFILE, LEGACY_JAR_MOD, UNSUPPORTED\n',
        "restore LEGACY_JAR_MOD installer format enum",
    )

    compat = src / "com/example/renderer/LwjglCompatibilityValidator.kt"
    text = compat.read_text(encoding="utf-8")
    old = '''                val glfwOk = glfwBytes.indexOf("glfwInit".toByteArray()) >= 0 &&\n                    glfwBytes.indexOf("glfwPollEvents".toByteArray()) >= 0\n                val callbackOk = listOf("receiveCallback", "nativeSendData", "nativeSetInputReady")\n                    .all { callbackBytes.indexOf(it.toByteArray()) >= 0 }\n'''
    new = '''                val glfwOk = containsBytes(glfwBytes, "glfwInit".toByteArray()) &&\n                    containsBytes(glfwBytes, "glfwPollEvents".toByteArray())\n                val callbackOk = listOf("receiveCallback", "nativeSendData", "nativeSetInputReady")\n                    .all { containsBytes(callbackBytes, it.toByteArray()) }\n'''
    if text.count(old) == 1:
        text = text.replace(old, new)
        text += '''\n\nprivate fun containsBytes(haystack: ByteArray, needle: ByteArray): Boolean {\n    if (needle.isEmpty()) return true\n    if (needle.size > haystack.size) return false\n    outer@ for (i in 0..haystack.size - needle.size) {\n        for (j in needle.indices) {\n            if (haystack[i + j] != needle[j]) continue@outer\n        }\n        return true\n    }\n    return false\n}\n'''
        compat.write_text(text, encoding="utf-8")
        print("[repair] fix LWJGL byte-subsequence validation")
    else:
        raise SystemExit(f"LWJGL compatibility block not found uniquely in {compat}")

    stub = src / "com/example/renderer/LwjglGlfwStubManager.kt"
    text = stub.read_text(encoding="utf-8")
    text2 = text.replace('                    callbackBytes.indexOf(symbol.toByteArray()) < 0', '                    !containsBytes(callbackBytes, symbol.toByteArray())')
    text2 = text2.replace('                if (glfwBytes.indexOf("glfwInit".toByteArray()) < 0 ||\n                    glfwBytes.indexOf("glfwPollEvents".toByteArray()) < 0) {', '                if (!containsBytes(glfwBytes, "glfwInit".toByteArray()) ||\n                    !containsBytes(glfwBytes, "glfwPollEvents".toByteArray())) {')
    if text2 == text:
        raise SystemExit(f"LWJGL GLFW stub byte-search expressions not found in {stub}")
    text2 += '''\n\nprivate fun containsBytes(haystack: ByteArray, needle: ByteArray): Boolean {\n    if (needle.isEmpty()) return true\n    if (needle.size > haystack.size) return false\n    outer@ for (i in 0..haystack.size - needle.size) {\n        for (j in needle.indices) {\n            if (haystack[i + j] != needle[j]) continue@outer\n        }\n        return true\n    }\n    return false\n}\n'''
    stub.write_text(text2, encoding="utf-8")
    print("[repair] fix GLFW stub byte-subsequence validation")

    native_dep = src / "com/example/renderer/NativeDependencyVerifier.kt"
    replace_once(
        native_dep,
        '        require(byte(header[0]) == 0x7f && header[1] == \'E\'.code.toByte() && header[2] == \'L\'.code.toByte() && header[3] == \'F\'.code.toByte()) { "not ELF" }\n',
        '        require(header[0] == 0x7f.toByte() && header[1] == \'E\'.code.toByte() && header[2] == \'L\'.code.toByte() && header[3] == \'F\'.code.toByte()) { "not ELF" }\n',
        "fix invalid byte() ELF header call",
    )

    home = src / "com/example/ui/screens/HomeScreen.kt"
    replace_once(
        home,
        '        modifier = Modifier.weight(1f).graphicsScale(scale).clickable(interactionSource = interaction, indication = null, onClick = onClick),\n',
        '        modifier = Modifier.graphicsScale(scale).clickable(interactionSource = interaction, indication = null, onClick = onClick),\n',
        "remove out-of-scope QuickAction weight modifier",
    )

    parser = src / "com/example/versions/VersionJsonParser.kt"
    replace_once(
        parser,
        '            val id = client.optString("argument", "${path}")\n                .removePrefix("${")\n                .removeSuffix("}")\n',
        '            val id = client.optString("argument", "\\${path}")\n                .removePrefix("\\${")\n                .removeSuffix("}")\n',
        "repair malformed logging argument template strings",
    )

    recovery = src / "com/example/logs/LaunchRecoveryPolicy.kt"
    old_recovery = '''    fun rendererFallbackFromPreviousCrash(rootDir: File, requested: RendererBackend): RendererBackend {\n        val latest = CrashDiagnostics.findLatestHotSpotError(rootDir) ?: return requested\n        val text = runCatching { latest.readText() }.getOrDefault("").lowercase()\n        if (text.isBlank()) return requested\n\n        val rendererCrash = listOf("libgl4es", "mobileglues", "libzink", "libvulkan", "glfw", "lwjgl", "egl").any { it in text }\n        if (rendererCrash && requested != RendererBackend.COMPATIBILITY) {\n            LauncherLogger.warn("Previous HotSpot native crash implicated graphics/native code (${latest.name}); using Compatibility renderer for this launch.")\n            return RendererBackend.COMPATIBILITY\n        }\n        return requested\n    }\n'''
    new_recovery = '''    fun rendererFallbackFromPreviousCrash(rootDir: File, requested: RendererBackend): RendererBackend {\n        val latest = rootDir.walkTopDown()\n            .filter { it.isFile }\n            .filter { it.name.startsWith("hs_err_pid") || it.name.contains("hotspot", ignoreCase = true) }\n            .maxByOrNull { it.lastModified() }\n            ?: return requested\n        val text = runCatching { latest.readText() }.getOrDefault("").lowercase()\n        if (text.isBlank()) return requested\n\n        val rendererCrash = listOf("libgl4es", "mobileglues", "libzink", "libvulkan", "glfw", "lwjgl", "egl").any { it in text }\n        if (rendererCrash && requested != RendererBackend.COMPATIBILITY) {\n            LauncherLogger.warn("Previous HotSpot native crash implicated graphics/native code (${latest.name}); using Compatibility renderer for this launch.")\n            return RendererBackend.COMPATIBILITY\n        }\n        return requested\n    }\n'''
    replace_once(recovery, old_recovery, new_recovery, "replace missing CrashDiagnostics hotspot lookup")

    print("[repair] Step 153 compile repairs complete")


if __name__ == "__main__":
    main()
