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
printf '%s\\n' "$PACKAGE" > "$OUT/package.txt"
printf '%s\\n' "$ACTIVITY" > "$OUT/activity.txt"

"$ADB" wait-for-device
"$ADB" uninstall "$PACKAGE" > "$OUT/uninstall.txt" 2>&1 || true
"$ADB" install "$APK" > "$OUT/install.txt" 2>&1
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c

DATA_ROOT="$($ADB shell run-as "$PACKAGE" sh -c 'pwd' | tr -d '\\r')"
test -n "$DATA_ROOT"
printf '%s\\n' "$DATA_ROOT" > "$OUT/app-data-root.txt"

ROOT_REL=""
ROOTS="$($ADB shell run-as "$PACKAGE" sh -c 'find . -type d -name versions -print 2>/dev/null | head -20' | tr -d '\\r')"
if [ -n "$ROOTS" ]; then
  ROOT_REL="$(printf '%s\\n' "$ROOTS" | head -n1 | sed 's#/versions$##')"
fi
if [ -z "$ROOT_REL" ]; then
  ROOT_REL="./minecraft"
  "$ADB" shell run-as "$PACKAGE" sh -c 'mkdir -p ./minecraft/versions ./minecraft/libraries ./minecraft/assets/indexes ./minecraft/assets/objects'
fi
printf '%s\\n' "$ROOT_REL" > "$OUT/minecraft-root.txt"
printf '%s\\n' "$ROOTS" > "$OUT/discovered-roots.txt"

STAGE="/data/local/tmp/craftdroid-step191-$RANDOM"
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

# Give Compose and the launcher state time to render, then find a Play/Start control.
# Parse the XML with Python so detection does not depend on the attribute order emitted
# by UIAutomator (text/content-desc/bounds can appear in different orders).
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
    label = f'{text} {desc}'.strip()
    if not re.search(r'(?i)\\b(play|start)\\b', label):
        continue
    bounds = node.attrib.get('bounds', '')
    m = re.fullmatch(r'\\[(\\d+),(\\d+)\\]\\[(\\d+),(\\d+)\\]', bounds)
    if m:
        print(' '.join(m.groups()))
        break
PY
)"

  if [ -n "$PLAY_BOUNDS" ]; then
    cp "$OUT/ui-${attempt}.xml" "$OUT/ui.xml"
    printf '%s\\n' "$attempt" > "$OUT/ui-attempt.txt"
    break
  fi
  sleep 2
done

if [ -n "$PLAY_BOUNDS" ]; then
  read -r x1 y1 x2 y2 <<< "$PLAY_BOUNDS"
  printf 'bounds=%s\\n' "$PLAY_BOUNDS" > "$OUT/play-target.txt"

  # Isolate the actual launch attempt from launcher startup noise. Any Minecraft
  # launch marker below must therefore be emitted after this Play/Start action.
  "$ADB" logcat -c
  "$ADB" logcat -b crash -c || true
  printf 'Logcat and crash buffer cleared immediately before Play/Start tap.\\n' > "$OUT/post-play-log-boundary.txt"
  "$ADB" shell input tap "$(( (x1+x2) / 2 ))" "$(( (y1+y2) / 2 ))" > "$OUT/play-tap.txt" 2>&1 || true
  printf 'Tapped production Play/Start control at %s\\n' "$PLAY_BOUNDS" | tee -a "$OUT/play-tap.txt"
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

for delay in 15 30 45 60; do
  sleep 15
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
  "$ADB" logcat -b crash -d -v threadtime > "$OUT/crash-logcat-${delay}s.txt" || true
done
"$ADB" shell dumpsys activity activities > "$OUT/activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/windows.txt" || true
"$ADB" shell ps -A > "$OUT/processes.txt" || true
cat "$OUT/logcat-60s.txt" > "$OUT/logcat.txt"
cat "$OUT/crash-logcat-60s.txt" > "$OUT/crash-logcat.txt"
grep -Ei 'CraftDroid|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt" || grep -Eiq "$FATAL_RE" "$OUT/crash-logcat.txt"; then
  echo 'Step 191 detected a real Android/JVM/native launch failure.' >&2
  grep -Eia "$FATAL_RE" "$OUT/logcat.txt" "$OUT/crash-logcat.txt" >&2 || true
  exit 1
fi

if [ -z "$PLAY_BOUNDS" ]; then
  echo 'Step 191 could not find a production Play/Start control, so no real launch attempt was made.' | tee "$OUT/result.txt"
  exit 1
fi

if grep -Eiq 'MinecraftLaunchManager.*launch|NativeGameBridge.*launchJava|LaunchPreflight.*valid|Minecraft.*starting|Step [1-6]/6:' "$OUT/logcat.txt"; then
  echo 'Step 191 reached the production Minecraft launch path after the Play/Start action without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
else
  echo 'Step 191 tapped the production Play/Start control and staged real Minecraft 1.21.1 files, but no post-Play Minecraft JVM launch marker was observed.' | tee "$OUT/result.txt"
  exit 1
fi
