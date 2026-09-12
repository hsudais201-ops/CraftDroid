#!/usr/bin/env bash
set -euo pipefail

APK="${1:?usage: runtime_smoke_step174.sh <apk> <output-dir>}"
OUT="${2:?usage: runtime_smoke_step174.sh <apk> <output-dir>}"
mkdir -p "$OUT"

ADB="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/platform-tools/adb"
AAPT="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools/36.0.0/aapt"

PACKAGE="$($AAPT dump badging "$APK" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -n1)"
ACTIVITY="$($AAPT dump badging "$APK" | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" | head -n1)"
test -n "$PACKAGE" || { echo 'Unable to determine APK package name' >&2; exit 1; }
test -n "$ACTIVITY" || { echo 'Unable to determine launchable activity' >&2; exit 1; }

printf '%s\n' "$PACKAGE" > "$OUT/package.txt"
printf '%s\n' "$ACTIVITY" > "$OUT/activity.txt"

"$ADB" wait-for-device
"$ADB" install -r "$APK"
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c
"$ADB" shell monkey -p "$PACKAGE" 1 >/dev/null
sleep 20
"$ADB" logcat -d -v threadtime > "$OUT/emulator-logcat.txt"
"$ADB" shell dumpsys activity activities > "$OUT/emulator-activities.txt" || true

if grep -Eiq 'FATAL EXCEPTION|Fatal signal|SIGSEGV|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|dlopen failed|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)' "$OUT/emulator-logcat.txt"; then
  echo 'Runtime smoke test found a fatal/native launch signature.' >&2
  grep -Ei 'FATAL EXCEPTION|Fatal signal|SIGSEGV|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|dlopen failed|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)' "$OUT/emulator-logcat.txt" >&2 || true
  exit 1
fi

printf '%s\n' 'PASS: APK installed and launcher activity started on Android emulator.' | tee "$OUT/result.txt"
