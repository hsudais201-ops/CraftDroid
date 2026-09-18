#!/usr/bin/env bash
set -euo pipefail

APK="${1:?usage: real_minecraft_boot_step182.sh <apk> <output-dir> <fixture-dir>}"
OUT="${2:?usage: real_minecraft_boot_step182.sh <apk> <output-dir> <fixture-dir>}"
FIXTURE="${3:?usage: real_minecraft_boot_step182.sh <apk> <output-dir> <fixture-dir>}"
mkdir -p "$OUT"
ADB="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/platform-tools/adb"
AAPT="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools/36.0.0/aapt"

PACKAGE="$($AAPT dump badging "$APK" | sed -n "s/^package: name='\\([^']*\\)'.*/\\1/p" | head -n1)"
ACTIVITY="$($AAPT dump badging "$APK" | sed -n "s/^launchable-activity: name='\\([^']*\\)'.*/\\1/p" | head -n1)"
test -n "$PACKAGE" && test -n "$ACTIVITY"
printf '%s\n' "$PACKAGE" > "$OUT/package.txt"
printf '%s\n' "$ACTIVITY" > "$OUT/activity.txt"

"$ADB" wait-for-device
"$ADB" uninstall "$PACKAGE" >/dev/null 2>&1 || true
"$ADB" install "$APK"
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c
"$ADB" shell logcat -b crash -c 2>/dev/null || true

DATA_ROOT="$($ADB shell run-as "$PACKAGE" sh -c 'pwd' | tr -d '\r')"
test -n "$DATA_ROOT"
printf '%s\n' "$DATA_ROOT" > "$OUT/app-data-root.txt"

ROOT_REL=""
ROOTS="$($ADB shell run-as "$PACKAGE" sh -c 'find . -type d -name versions -print 2>/dev/null | head -20' | tr -d '\r')"
if [ -n "$ROOTS" ]; then
  ROOT_REL="$(printf '%s\n' "$ROOTS" | head -n1 | sed 's#/versions$##')"
fi
if [ -z "$ROOT_REL" ]; then
  ROOT_REL="./minecraft"
  "$ADB" shell run-as "$PACKAGE" sh -c 'mkdir -p ./minecraft/versions ./minecraft/libraries ./minecraft/assets/indexes ./minecraft/assets/objects'
fi
printf '%s\n' "$ROOT_REL" > "$OUT/minecraft-root.txt"
printf '%s\n' "$ROOTS" > "$OUT/discovered-roots.txt"

STAGE="/data/local/tmp/craftdroid-step197-$RANDOM"
"$ADB" shell rm -rf "$STAGE"
"$ADB" shell mkdir -p "$STAGE"
"$ADB" push "$FIXTURE/." "$STAGE/" > "$OUT/fixture-push.txt"
"$ADB" shell run-as "$PACKAGE" sh -c "rm -rf '$ROOT_REL/versions/1.21.1' '$ROOT_REL/libraries' '$ROOT_REL/assets'; mkdir -p '$ROOT_REL'; cp -R '$STAGE/versions' '$ROOT_REL/'; cp -R '$STAGE/libraries' '$ROOT_REL/'; cp -R '$STAGE/assets' '$ROOT_REL/'"
"$ADB" shell rm -rf "$STAGE"

ASSET_INDEX_NAME="$(find "$FIXTURE/assets/indexes" -type f -name '*.json' -print -quit | xargs -r basename)"
test -n "$ASSET_INDEX_NAME"
"$ADB" shell run-as "$PACKAGE" sh -c "test -s '$ROOT_REL/versions/1.21.1/1.21.1.jar' && test -s '$ROOT_REL/versions/1.21.1/1.21.1.json' && find '$ROOT_REL/libraries' -type f | grep -q . && test -s '$ROOT_REL/assets/indexes/$ASSET_INDEX_NAME'" > "$OUT/staged-fixture-check.txt"

if ! "$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" > "$OUT/activity-start.txt" 2>&1; then
  "$ADB" shell monkey -p "$PACKAGE" 1 > "$OUT/monkey-start.txt" 2>&1
fi

"$ADB" shell dumpsys activity activities > "$OUT/pre-play-activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/pre-play-windows.txt" || true
"$ADB" shell pidof "$PACKAGE" > "$OUT/pre-play-pid.txt" 2>/dev/null || true
"$ADB" exec-out screencap -p > "$OUT/before-play.png" 2>/dev/null || true

PLAY_BOUNDS=""
for attempt in $(seq 1 12); do
  "$ADB" shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
  "$ADB" shell cat /sdcard/window.xml > "$OUT/ui-${attempt}.xml" 2>/dev/null || true
  PLAY_BOUNDS="$(python3 - "$OUT/ui-${attempt}.xml" <<'PY'
import re
import sys
import xml.etree.ElementTree as ET
path = sys.argv[1]
try:
    root = ET.parse(path).getroot()
except (OSError, ET.ParseError):
    print('')
    raise SystemExit(0)
for node in root.iter('node'):
    text = node.attrib.get('text', '')
    desc = node.attrib.get('content-desc', '')
    if not re.search(r'(?i)\b(play|start)\b', f'{text} {desc}'.strip()):
        continue
    m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if m:
        print(' '.join(m.groups()))
        break
PY
)"
  if [ -z "$PLAY_BOUNDS" ] && [ -f "$OUT/ui-12.xml" ]; then
  INSTALL_BOUNDS="$(python3 - "$OUT/ui-12.xml" <<'PY'
import re, sys, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except (OSError, ET.ParseError):
    print('')
    raise SystemExit(0)
for node in root.iter('node'):
    text = node.attrib.get('text', '')
    desc = node.attrib.get('content-desc', '')
    if re.search(r'(?i)^\s*install\s*    cp "$OUT/ui-${attempt}.xml" "$OUT/ui.xml"
    printf '%s\n' "$attempt" > "$OUT/ui-attempt.txt"
    break
  fi
  sleep 2
done

if [ -n "$PLAY_BOUNDS" ]; then
  read -r x1 y1 x2 y2 <<< "$PLAY_BOUNDS"
  printf 'bounds=%s\n' "$PLAY_BOUNDS" > "$OUT/play-target.txt"
  "$ADB" logcat -c
  "$ADB" shell logcat -b crash -c 2>/dev/null || true
  printf 'Logcat cleared immediately before Play/Start tap.\n' > "$OUT/post-play-log-boundary.txt"
  "$ADB" shell input tap "$(( (x1+x2) / 2 ))" "$(( (y1+y2) / 2 ))" > "$OUT/play-tap.txt" 2>&1 || true
  printf 'Tapped production Play/Start control at %s\n' "$PLAY_BOUNDS" | tee -a "$OUT/play-tap.txt"
  sleep 3
  "$ADB" shell dumpsys activity activities > "$OUT/post-play-activities.txt" || true
  "$ADB" shell dumpsys window windows > "$OUT/post-play-windows.txt" || true
  "$ADB" shell pidof "$PACKAGE" > "$OUT/post-play-pid.txt" 2>/dev/null || true
  "$ADB" exec-out screencap -p > "$OUT/after-play.png" 2>/dev/null || true
  "$ADB" shell uiautomator dump /sdcard/window-after-play.xml >/dev/null 2>&1 || true
  "$ADB" shell cat /sdcard/window-after-play.xml > "$OUT/ui-after-play.xml" 2>/dev/null || true
else
  echo 'No accessibility-visible Play/Start control found after 24 seconds.' > "$OUT/play-tap.txt"
  [ -f "$OUT/ui-12.xml" ] && cp "$OUT/ui-12.xml" "$OUT/ui.xml"
fi

# Periodically capture process/native state during the real launch window.
for delay in 15 30 45 60; do
  sleep 15
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
  "$ADB" logcat -b crash -d -v threadtime > "$OUT/crash-logcat-${delay}s.txt" || true
  "$ADB" shell pidof "$PACKAGE" > "$OUT/pid-${delay}s.txt" 2>/dev/null || true
  : > "$OUT/process-${delay}s.txt"
  : > "$OUT/native-maps-${delay}s.txt"
  while read -r pid; do
    [ -n "$pid" ] || continue
    echo "PID=$pid" >> "$OUT/process-${delay}s.txt"
    "$ADB" shell sh -c "tr '\0' ' ' < /proc/$pid/cmdline" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- /proc/%s/status ---\n' "$pid" >> "$OUT/process-${delay}s.txt"
    "$ADB" shell sh -c "grep -E '^(Name|State|VmRSS|Threads):' /proc/$pid/status" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- loaded native mappings ---\n' >> "$OUT/native-maps-${delay}s.txt"
    "$ADB" shell sh -c "grep -E 'libcraftdroidbridge|libc\+\+|liblwjgl|libglfw|libEGL|libGLES|libopenal|libjli|libart' /proc/$pid/maps" >> "$OUT/native-maps-${delay}s.txt" 2>/dev/null || true
  done < "$OUT/pid-${delay}s.txt"
done

"$ADB" shell dumpsys activity activities > "$OUT/activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/windows.txt" || true
"$ADB" shell ps -A > "$OUT/processes.txt" || true
cat "$OUT/logcat-60s.txt" > "$OUT/logcat.txt"
cat "$OUT/crash-logcat-60s.txt" > "$OUT/crash-logcat.txt"
printf '%s\n' "$OUT/native-maps-60s.txt" > "$OUT/native-maps-latest.txt"
printf '%s\n' "$OUT/process-60s.txt" > "$OUT/process-latest.txt"
grep -Ei 'CraftDroid|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt" || grep -Eiq "$FATAL_RE" "$OUT/crash-logcat.txt"; then
  echo 'Step 197 detected a real Android/JVM/native launch failure.' >&2
  grep -Eia "$FATAL_RE" "$OUT/logcat.txt" "$OUT/crash-logcat.txt" >&2 || true
  exit 1
fi

if [ -z "$PLAY_BOUNDS" ]; then
  echo 'Step 197 could not find a production Play/Start control, so no real launch attempt was made.' | tee "$OUT/result.txt"
  exit 1
fi

if grep -Eiq 'MinecraftLaunchManager.*launch|NativeGameBridge.*launchJava|LaunchPreflight.*valid|Minecraft.*starting|Step [1-6]/6:' "$OUT/logcat.txt"; then
  echo 'Step 197 reached the production Minecraft launch path after Play/Start without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
else
  echo 'Step 197 tapped Play/Start and staged real Minecraft 1.21.1 files, but no post-Play Minecraft JVM launch marker was observed.' | tee "$OUT/result.txt"
  exit 1
fi, f'{text} {desc}'.strip()):
        m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
        if m:
            print(' '.join(m.groups()))
            break
PY
)"
  if [ -n "$INSTALL_BOUNDS" ]; then
    read -r ix1 iy1 ix2 iy2 <<< "$INSTALL_BOUNDS"
    printf 'Fresh install gate detected; tapping INSTALL at [%s,%s][%s,%s].\n' "$ix1" "$iy1" "$ix2" "$iy2" | tee "$OUT/first-run-install-tap.txt"
    "$ADB" shell input tap "$(( (ix1+ix2) / 2 ))" "$(( (iy1+iy2) / 2 ))" >> "$OUT/first-run-install-tap.txt" 2>&1 || true
    sleep 4
    for attempt in $(seq 1 12); do
      "$ADB" shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
      "$ADB" shell cat /sdcard/window.xml > "$OUT/post-install-ui-${attempt}.xml" 2>/dev/null || true
      PLAY_BOUNDS="$(python3 - "$OUT/post-install-ui-${attempt}.xml" <<'PY'
import re, sys, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except (OSError, ET.ParseError):
    print('')
    raise SystemExit(0)
for node in root.iter('node'):
    text = node.attrib.get('text', '')
    desc = node.attrib.get('content-desc', '')
    if not re.search(r'(?i)\b(play|start)\b', f'{text} {desc}'.strip()):
        continue
    m = re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', node.attrib.get('bounds', ''))
    if m:
        print(' '.join(m.groups()))
        break
PY
)"
      if [ -n "$PLAY_BOUNDS" ]; then
        cp "$OUT/post-install-ui-${attempt}.xml" "$OUT/ui.xml"
        printf '%s\n' "${attempt}" > "$OUT/ui-attempt.txt"
        break
      fi
      sleep 2
    done
  fi
fi

if [ -n "$PLAY_BOUNDS" ]; then
    cp "$OUT/ui-${attempt}.xml" "$OUT/ui.xml"
    printf '%s\n' "$attempt" > "$OUT/ui-attempt.txt"
    break
  fi
  sleep 2
done

if [ -n "$PLAY_BOUNDS" ]; then
  read -r x1 y1 x2 y2 <<< "$PLAY_BOUNDS"
  printf 'bounds=%s\n' "$PLAY_BOUNDS" > "$OUT/play-target.txt"
  "$ADB" logcat -c
  "$ADB" shell logcat -b crash -c 2>/dev/null || true
  printf 'Logcat cleared immediately before Play/Start tap.\n' > "$OUT/post-play-log-boundary.txt"
  "$ADB" shell input tap "$(( (x1+x2) / 2 ))" "$(( (y1+y2) / 2 ))" > "$OUT/play-tap.txt" 2>&1 || true
  printf 'Tapped production Play/Start control at %s\n' "$PLAY_BOUNDS" | tee -a "$OUT/play-tap.txt"
  sleep 3
  "$ADB" shell dumpsys activity activities > "$OUT/post-play-activities.txt" || true
  "$ADB" shell dumpsys window windows > "$OUT/post-play-windows.txt" || true
  "$ADB" shell pidof "$PACKAGE" > "$OUT/post-play-pid.txt" 2>/dev/null || true
  "$ADB" exec-out screencap -p > "$OUT/after-play.png" 2>/dev/null || true
  "$ADB" shell uiautomator dump /sdcard/window-after-play.xml >/dev/null 2>&1 || true
  "$ADB" shell cat /sdcard/window-after-play.xml > "$OUT/ui-after-play.xml" 2>/dev/null || true
else
  echo 'No accessibility-visible Play/Start control found after 24 seconds.' > "$OUT/play-tap.txt"
  [ -f "$OUT/ui-12.xml" ] && cp "$OUT/ui-12.xml" "$OUT/ui.xml"
fi

# Periodically capture process/native state during the real launch window.
for delay in 15 30 45 60; do
  sleep 15
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
  "$ADB" logcat -b crash -d -v threadtime > "$OUT/crash-logcat-${delay}s.txt" || true
  "$ADB" shell pidof "$PACKAGE" > "$OUT/pid-${delay}s.txt" 2>/dev/null || true
  : > "$OUT/process-${delay}s.txt"
  : > "$OUT/native-maps-${delay}s.txt"
  while read -r pid; do
    [ -n "$pid" ] || continue
    echo "PID=$pid" >> "$OUT/process-${delay}s.txt"
    "$ADB" shell sh -c "tr '\0' ' ' < /proc/$pid/cmdline" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- /proc/%s/status ---\n' "$pid" >> "$OUT/process-${delay}s.txt"
    "$ADB" shell sh -c "grep -E '^(Name|State|VmRSS|Threads):' /proc/$pid/status" >> "$OUT/process-${delay}s.txt" 2>/dev/null || true
    printf '\n--- loaded native mappings ---\n' >> "$OUT/native-maps-${delay}s.txt"
    "$ADB" shell sh -c "grep -E 'libcraftdroidbridge|libc\+\+|liblwjgl|libglfw|libEGL|libGLES|libopenal|libjli|libart' /proc/$pid/maps" >> "$OUT/native-maps-${delay}s.txt" 2>/dev/null || true
  done < "$OUT/pid-${delay}s.txt"
done

"$ADB" shell dumpsys activity activities > "$OUT/activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/windows.txt" || true
"$ADB" shell ps -A > "$OUT/processes.txt" || true
cat "$OUT/logcat-60s.txt" > "$OUT/logcat.txt"
cat "$OUT/crash-logcat-60s.txt" > "$OUT/crash-logcat.txt"
printf '%s\n' "$OUT/native-maps-60s.txt" > "$OUT/native-maps-latest.txt"
printf '%s\n' "$OUT/process-60s.txt" > "$OUT/process-latest.txt"
grep -Ei 'CraftDroid|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt" || grep -Eiq "$FATAL_RE" "$OUT/crash-logcat.txt"; then
  echo 'Step 197 detected a real Android/JVM/native launch failure.' >&2
  grep -Eia "$FATAL_RE" "$OUT/logcat.txt" "$OUT/crash-logcat.txt" >&2 || true
  exit 1
fi

if [ -z "$PLAY_BOUNDS" ]; then
  echo 'Step 197 could not find a production Play/Start control, so no real launch attempt was made.' | tee "$OUT/result.txt"
  exit 1
fi

if grep -Eiq 'MinecraftLaunchManager.*launch|NativeGameBridge.*launchJava|LaunchPreflight.*valid|Minecraft.*starting|Step [1-6]/6:' "$OUT/logcat.txt"; then
  echo 'Step 197 reached the production Minecraft launch path after Play/Start without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
else
  echo 'Step 197 tapped Play/Start and staged real Minecraft 1.21.1 files, but no post-Play Minecraft JVM launch marker was observed.' | tee "$OUT/result.txt"
  exit 1
fi