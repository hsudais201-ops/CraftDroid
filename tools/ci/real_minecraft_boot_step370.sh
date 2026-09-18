#!/usr/bin/env bash
set -euo pipefail

APK="${1:?usage: real_minecraft_boot_step370.sh <apk> <output-dir> <fixture-dir>}"
OUT="${2:?usage: real_minecraft_boot_step370.sh <apk> <output-dir> <fixture-dir>}"
FIXTURE="${3:?usage: real_minecraft_boot_step370.sh <apk> <output-dir> <fixture-dir>}"
mkdir -p "$OUT"

SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
test -n "$SDK_ROOT"
ADB_BIN="$SDK_ROOT/platform-tools/adb"
AAPT="$SDK_ROOT/build-tools/36.0.0/aapt"
test -x "$ADB_BIN"
test -x "$AAPT"

ADB_SERIAL="${ANDROID_SERIAL:-}"
adb() {
  if [ -n "$ADB_SERIAL" ]; then
    "$ADB_BIN" -s "$ADB_SERIAL" "$@"
  else
    "$ADB_BIN" "$@"
  fi
}

phase() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" | tee -a "$OUT/phase.log"
}

phase 'START'
printf '%s\n' "$APK" > "$OUT/apk-path.txt"
printf '%s\n' "$FIXTURE" > "$OUT/fixture-path.txt"
printf '%s\n' "${ADB_SERIAL:-default}" > "$OUT/adb-serial.txt"

phase 'APK_BADGING'
BADGING="$OUT/apk-badging.txt"
"$AAPT" dump badging "$APK" > "$BADGING"
PACKAGE="$(sed -n "s/^package: name='\([^']*\)'.*/\1/p" "$BADGING")"
ACTIVITY="$(sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" "$BADGING")"
test -n "$PACKAGE"
test -n "$ACTIVITY"
printf '%s\n' "$PACKAGE" > "$OUT/package.txt"
printf '%s\n' "$ACTIVITY" > "$OUT/activity.txt"

phase 'ADB_WAIT'
adb wait-for-device

phase 'ANDROID_BOOT_WAIT'
BOOTED=''
for attempt in $(seq 1 900); do
  BOOTED="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r\n' || true)"
  if [ "$BOOTED" = '1' ]; then
    printf 'boot_completed=1 after attempt=%s\n' "$attempt" | tee "$OUT/android-boot-complete.txt"
    break
  fi
  if (( attempt % 30 == 0 )); then
    adb shell getprop ro.build.version.sdk > "$OUT/sdk-during-boot.txt" 2>/dev/null || true
    printf 'waiting-for-boot attempt=%s state=%s\n' "$attempt" "${BOOTED:-unknown}" | tee -a "$OUT/boot-wait.log"
  fi
  sleep 2
done
test "$BOOTED" = '1'

phase 'ADB_READY_WAIT'
STATE=''
for attempt in $(seq 1 30); do
  STATE="$(adb get-state 2>/dev/null | tr -d '\r\n' || true)"
  if [ "$STATE" = 'device' ]; then
    printf 'state=%s after attempt=%s\n' "$STATE" "$attempt" | tee "$OUT/adb-ready.txt"
    break
  fi
  if (( attempt % 5 == 0 )); then
    printf 'waiting-for-adb-ready attempt=%s state=%s\n' "$attempt" "${STATE:-unknown}" | tee -a "$OUT/boot-wait.log"
  fi
  sleep 2
done
if [ "$STATE" != 'device' ]; then
  adb reconnect offline >/dev/null 2>&1 || true
  STATE="$(adb get-state 2>/dev/null | tr -d '\r\n' || true)"
fi
test "$STATE" = 'device'

phase 'DEVICE_INFO'
adb shell getprop ro.product.cpu.abi | tee "$OUT/emulator-abi.txt"
adb shell getprop ro.build.version.sdk | tee "$OUT/emulator-api.txt"
adb shell getprop ro.product.model | tee "$OUT/emulator-model.txt"
adb shell settings put global window_animation_scale 0 >/dev/null 2>&1 || true
adb shell settings put global transition_animation_scale 0 >/dev/null 2>&1 || true
adb shell settings put global animator_duration_scale 0 >/dev/null 2>&1 || true

phase 'INSTALL_APK'
adb uninstall "$PACKAGE" >/dev/null 2>&1 || true
INSTALL_LOG="$OUT/apk-install.txt"
if [ -n "$ADB_SERIAL" ]; then
  if ! timeout 300 "$ADB_BIN" -s "$ADB_SERIAL" install "$APK" > "$INSTALL_LOG" 2>&1; then
    cat "$INSTALL_LOG" >&2 || true
    phase 'INSTALL_APK_FAILED'
    exit 1
  fi
else
  if ! timeout 300 "$ADB_BIN" install "$APK" > "$INSTALL_LOG" 2>&1; then
    cat "$INSTALL_LOG" >&2 || true
    phase 'INSTALL_APK_FAILED'
    exit 1
  fi
fi
cat "$INSTALL_LOG"
adb shell pm path "$PACKAGE" | tee "$OUT/pm-path.txt"
adb shell dumpsys package "$PACKAGE" > "$OUT/package-dump.txt" || true

phase 'APP_DATA_DISCOVERY'
DATA_ROOT="$(adb shell run-as "$PACKAGE" sh -c 'pwd' | tr -d '\r')"
test -n "$DATA_ROOT"
printf '%s\n' "$DATA_ROOT" > "$OUT/app-data-root.txt"
ROOTS="$(adb shell run-as "$PACKAGE" sh -c 'find . -type d -name versions -print 2>/dev/null | head -20' | tr -d '\r')"
ROOT_REL=''
if [ -n "$ROOTS" ]; then
  ROOT_REL="$(printf '%s\n' "$ROOTS" | sed -n '1p' | sed 's#/versions$##')"
fi
if [ -z "$ROOT_REL" ]; then
  ROOT_REL='./minecraft'
  adb shell run-as "$PACKAGE" sh -c 'mkdir -p ./minecraft/versions ./minecraft/libraries ./minecraft/assets/indexes ./minecraft/assets/objects'
fi
printf '%s\n' "$ROOT_REL" > "$OUT/minecraft-root.txt"
printf '%s\n' "$ROOTS" > "$OUT/discovered-roots.txt"

phase 'STAGE_FIXTURE'
ASSET_INDEX_NAME="$(find "$FIXTURE/assets/indexes" -type f -name '*.json' -print -quit | xargs -r basename)"
test -n "$ASSET_INDEX_NAME"
STAGE="/data/local/tmp/craftdroid-step370-$RANDOM"
adb shell rm -rf "$STAGE"
adb shell mkdir -p "$STAGE"
adb push "$FIXTURE/." "$STAGE/" > "$OUT/fixture-push.txt"
adb shell run-as "$PACKAGE" sh -c "rm -rf '$ROOT_REL/versions/1.21.1' '$ROOT_REL/libraries' '$ROOT_REL/assets'; mkdir -p '$ROOT_REL'; cp -R '$STAGE/versions' '$ROOT_REL/'; cp -R '$STAGE/libraries' '$ROOT_REL/'; cp -R '$STAGE/assets' '$ROOT_REL/'"
adb shell rm -rf "$STAGE"
adb shell run-as "$PACKAGE" sh -c "test -s '$ROOT_REL/versions/1.21.1/1.21.1.jar' && test -s '$ROOT_REL/versions/1.21.1/1.21.1.json' && find '$ROOT_REL/libraries' -type f | grep -q . && test -s '$ROOT_REL/assets/indexes/$ASSET_INDEX_NAME'" > "$OUT/staged-fixture-check.txt"

phase 'APP_START'
adb logcat -c
adb shell logcat -b crash -c 2>/dev/null || true
if ! adb shell am start -W -n "$PACKAGE/$ACTIVITY" > "$OUT/activity-start.txt" 2>&1; then
  adb shell monkey -p "$PACKAGE" 1 > "$OUT/monkey-start.txt" 2>&1 || true
fi
adb shell pidof "$PACKAGE" > "$OUT/pre-play-pid.txt" 2>/dev/null || true
adb exec-out screencap -p > "$OUT/before-play.png" 2>/dev/null || true
adb shell dumpsys activity activities > "$OUT/pre-play-activities.txt" || true

phase 'PLAY_CONTROL_DISCOVERY'
PLAY_BOUNDS=''
for attempt in $(seq 1 30); do
  adb shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/window.xml > "$OUT/ui-${attempt}.xml" 2>/dev/null || true
  PLAY_BOUNDS="$(python3 - "$OUT/ui-${attempt}.xml" <<'PY'
import re
import sys
import xml.etree.ElementTree as ET
path = sys.argv[1]
try:
    root = ET.parse(path).getroot()
except (OSError, ET.ParseError):
    raise SystemExit(0)
for node in root.iter('node'):
    text = node.attrib.get('text', '')
    desc = node.attrib.get('content-desc', '')
    value = f'{text} {desc}'.strip()
    if not re.search(r'(?i)\b(play|start)\b', value):
        continue
    m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if m:
        print(' '.join(m.groups()))
        raise SystemExit(0)
PY
)"
  if [ -n "$PLAY_BOUNDS" ]; then
    cp "$OUT/ui-${attempt}.xml" "$OUT/ui.xml"
    printf '%s\n' "$attempt" > "$OUT/ui-attempt.txt"
    break
  fi
  sleep 2
done

if [ -z "$PLAY_BOUNDS" ]; then
  printf '%s\n' 'No accessibility-visible Play/Start control found.' | tee "$OUT/result.txt"
  adb shell uiautomator dump /sdcard/window-final.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/window-final.xml > "$OUT/ui-final.xml" 2>/dev/null || true
  adb shell dumpsys activity activities > "$OUT/activities.txt" || true
  adb shell dumpsys window windows > "$OUT/windows.txt" || true
  adb logcat -d -v threadtime > "$OUT/logcat.txt" || true
  exit 1
fi

phase 'PLAY_TAP'
read -r x1 y1 x2 y2 <<< "$PLAY_BOUNDS"
printf 'bounds=%s\n' "$PLAY_BOUNDS" | tee "$OUT/play-target.txt"
adb logcat -c
adb shell logcat -b crash -c 2>/dev/null || true
adb shell input tap "$(( (x1+x2) / 2 ))" "$(( (y1+y2) / 2 ))" > "$OUT/play-tap.txt" 2>&1
printf 'Tapped Play/Start at %s\n' "$PLAY_BOUNDS" | tee -a "$OUT/play-tap.txt"

phase 'POST_PLAY_MONITOR'
for delay in 15 30 45 60 90 120 150 180; do
  sleep 15
  adb logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
  adb logcat -b crash -d -v threadtime > "$OUT/crash-logcat-${delay}s.txt" 2>/dev/null || true
  adb shell pidof "$PACKAGE" > "$OUT/pid-${delay}s.txt" 2>/dev/null || true
  adb shell dumpsys activity activities > "$OUT/activities-${delay}s.txt" || true
  : > "$OUT/process-${delay}s.txt"
  : > "$OUT/native-maps-${delay}s.txt"
  while read -r pid; do
    [ -n "$pid" ] || continue
    printf 'PID=%s\n' "$pid" >> "$OUT/process-${delay}s.txt"
    adb shell sh -c "tr '\0' ' ' < /proc/$pid/cmdline" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- status ---\n' >> "$OUT/process-${delay}s.txt"
    adb shell sh -c "grep -E '^(Name|State|VmRSS|Threads):' /proc/$pid/status" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- native maps ---\n' >> "$OUT/native-maps-${delay}s.txt"
    adb shell sh -c "grep -E 'libcraftdroidbridge|liblwjgl|libglfw|libEGL|libGLES|libopenal|libjli|libart' /proc/$pid/maps" >> "$OUT/native-maps-${delay}s.txt" 2>/dev/null || true
  done < "$OUT/pid-${delay}s.txt"
done

phase 'FINAL_CAPTURE'
adb shell dumpsys activity activities > "$OUT/activities.txt" || true
adb shell dumpsys window windows > "$OUT/windows.txt" || true
adb shell ps -A > "$OUT/processes.txt" || true
adb logcat -d -v threadtime > "$OUT/logcat.txt"
adb logcat -b crash -d -v threadtime > "$OUT/crash-logcat.txt" 2>/dev/null || true
grep -Ei 'CraftDroid|Droid Launcher|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt" || grep -Eiq "$FATAL_RE" "$OUT/crash-logcat.txt"; then
  phase 'FATAL_RUNTIME_ERROR'
  grep -Eia "$FATAL_RE" "$OUT/logcat.txt" "$OUT/crash-logcat.txt" >&2 || true
  printf '%s\n' 'Real Android/JVM/native launch failure detected.' | tee "$OUT/result.txt"
  exit 1
fi

if grep -Eiq 'MinecraftLaunchManager.*launch|NativeGameBridge.*launchJava|LaunchPreflight.*valid|Minecraft.*starting|Step [1-6]/6:' "$OUT/logcat.txt"; then
  phase 'MINECRAFT_LAUNCH_MARKER'
  printf '%s\n' 'Play/Start reached the production Minecraft launch path without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
  exit 0
fi

if grep -Eiq 'am_proc_start|ActivityTaskManager.*START|Starting: Intent|Process.*com\.craftdroid\.launcher' "$OUT/logcat.txt" && grep -Eiq 'libcraftdroidbridge|Minecraft|NativeGameBridge|LaunchPreflight' "$OUT/filtered-launch-log.txt"; then
  phase 'SECONDARY_LAUNCH_EVIDENCE'
  printf '%s\n' 'Play/Start produced secondary production launch evidence without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
  exit 0
fi

phase 'NO_LAUNCH_MARKER'
printf '%s\n' 'Play/Start was tapped and real Minecraft 1.21.1 was staged, but no production Minecraft launch marker was observed.' | tee "$OUT/result.txt"
exit 1