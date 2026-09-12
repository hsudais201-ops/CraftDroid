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
"$ADB" shell dumpsys window windows > "$OUT/emulator-windows.txt" || true

PID="$($ADB shell pidof "$PACKAGE" | tr -d '\r' | awk '{print $1}')"
if [ -z "$PID" ]; then
  echo 'Launcher process exited during runtime smoke test.' >&2
  exit 1
fi
printf '%s\n' "$PID" > "$OUT/pid.txt"

TOP_ACTIVITY="$($ADB shell dumpsys activity activities | sed -n 's/.*mResumedActivity:.* \([^ ]*\/[^ ]*\) .*/\1/p' | head -n1 | tr -d '\r')"
printf '%s\n' "$TOP_ACTIVITY" > "$OUT/top-activity.txt"
case "$TOP_ACTIVITY" in
  "$PACKAGE"/*) ;;
  *) echo "Launcher activity is not the resumed foreground activity: $TOP_ACTIVITY" >&2; exit 1 ;;
esac

"$ADB" shell cat "/proc/$PID/maps" > "$OUT/process-maps.txt" || true
if grep -Fq 'libcraftdroidbridge.so' "$OUT/process-maps.txt"; then
  printf '%s\n' 'native-bridge: loaded' > "$OUT/native-bridge.txt"
else
  printf '%s\n' 'native-bridge: not observed in launcher process (may be loaded lazily)' > "$OUT/native-bridge.txt"
fi

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|dlopen failed|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/emulator-logcat.txt"; then
  echo 'Runtime smoke test found a fatal/native launch signature.' >&2
  grep -Ei "$FATAL_RE" "$OUT/emulator-logcat.txt" >&2 || true
  exit 1
fi

printf '%s\n' 'PASS: APK installed, launcher process stayed alive, and launcher activity remained foreground on Android emulator.' | tee "$OUT/result.txt"
