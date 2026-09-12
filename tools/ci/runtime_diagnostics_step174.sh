#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-runtime-diagnostics}"
mkdir -p "$OUT"

log() { printf '[craftdroid-runtime] %s\n' "$*"; }

if command -v adb >/dev/null 2>&1 && adb get-state >/dev/null 2>&1; then
  log "Android device detected"
  adb shell getprop ro.product.cpu.abi > "$OUT/device_abi.txt" || true
  adb shell getprop ro.build.version.sdk > "$OUT/device_sdk.txt" || true
  adb shell getprop ro.opengles.version > "$OUT/opengles_version.txt" || true
  adb shell dumpsys activity activities > "$OUT/activities.txt" || true
  adb logcat -d -v threadtime > "$OUT/logcat.txt" || true
  adb logcat -d -v threadtime '*:E' > "$OUT/logcat_errors.txt" || true

  grep -E 'CraftDroid|craftdroid|GLFW|LWJGL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|SIGSEGV|Fatal signal|OutOfMemoryError|JNI|dlopen' \
    "$OUT/logcat.txt" > "$OUT/launch_failures.txt" || true

  log "Captured Android runtime diagnostics"
else
  log "No Android device/emulator available; runtime capture skipped"
  printf '%s\n' 'NO_DEVICE_AVAILABLE' > "$OUT/device_status.txt"
fi

printf '%s\n' 'Step 174 runtime diagnostics: complete' > "$OUT/status.txt"
