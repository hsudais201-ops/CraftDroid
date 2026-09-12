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
"$ADB" shell getprop sys.boot_completed > "$OUT/boot-completed.txt" || true
"$ADB" install -r "$APK"
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c

# Prefer an explicit activity launch so the test exercises the real entry point.
# Fall back to monkey for manifest/activity layouts that reject am start.
if ! "$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" > "$OUT/activity-start.txt" 2>&1; then
  "$ADB" shell monkey -p "$PACKAGE" 1 > "$OUT/monkey-start.txt" 2>&1
fi

# Capture startup progressively so short-lived native/JVM failures are retained.
for delay in 5 10 15; do
  sleep 5
  "$ADB" logcat -d -v threadtime > "$OUT/emulator-logcat-${delay}s.txt"
done
"$ADB" logcat -d -v threadtime > "$OUT/emulator-logcat.txt"
"$ADB" shell dumpsys activity activities > "$OUT/emulator-activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/emulator-windows.txt" || true

PID="$($ADB shell pidof "$PACKAGE" | tr -d '\r' | awk '{print $1}')"
if [ -z "$PID" ]; then
  echo 'Launcher process exited during runtime smoke test.' >&2
  tail -n 200 "$OUT/emulator-logcat.txt" >&2 || true
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

grep -Ei 'CraftDroid|craftdroid|GLFW|LWJGL|JavaRuntime|Renderer|NativeGameBridge|libcraftdroidbridge' "$OUT/emulator-logcat.txt" > "$OUT/launcher-startup-markers.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|linker.*CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)|ANativeWindow.*(fail|error)|EGL.*(error|fail)'
if grep -Eiq "$FATAL_RE" "$OUT/emulator-logcat.txt"; then
  echo 'Runtime smoke test found a fatal/native launch signature.' >&2
  grep -Ei "$FATAL_RE" "$OUT/emulator-logcat.txt" >&2 || true
  exit 1
fi

printf '%s\n' 'PASS: APK installed, launcher activity started, launcher process stayed alive, foreground activity remained CraftDroid, and no fatal Android/native/GLFW/LWJGL startup signature was detected.' | tee "$OUT/result.txt"
printf '%s\n' 'SCOPE: This smoke test verifies Android launcher startup/runtime health. It does not claim full Minecraft game boot without game assets/runtime/account setup.' > "$OUT/scope.txt"
