from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
kt = (ROOT / "app/src/main/java/com/example/game/NativeGameBridge.kt").read_text()
cpp = (ROOT / "app/src/main/cpp/craftdroidbridge.cpp").read_text()

assert "nativeValidateGlfwHandshake" in kt
assert "Java_com_example_game_NativeGameBridge_nativeValidateGlfwHandshake" in cpp

symbols = [
    "glfwInit", "glfwTerminate", "glfwCreateWindow",
    "glfwMakeContextCurrent", "glfwGetCurrentContext",
    "glfwSwapBuffers", "glfwPollEvents", "glfwSetWindowSize",
    "Java_org_lwjgl_glfw_CallbackBridge_nativeSendData",
    "Java_org_lwjgl_glfw_CallbackBridge_nativeSetInputReady",
    "Java_org_lwjgl_glfw_CallbackBridge_nativeClipboard",
    "Java_org_lwjgl_glfw_CallbackBridge_nativeSetGrabbing",
]
for symbol in symbols:
    assert symbol in cpp, f"missing native handshake symbol: {symbol}"

print("LWJGL handshake source verification: PASS")
