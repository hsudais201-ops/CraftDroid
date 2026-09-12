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
"$ADB" install -r "$APK"
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c

# Discover the launcher data root after installation. A fresh install may not yet
# have a versions/ directory, so create the stable game root deterministically.
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

# Stage the real Mojang fixture using the debuggable APK's run-as context.
STAGE="/data/local/tmp/craftdroid-step182-$RANDOM"
"$ADB" shell rm -rf "$STAGE"
"$ADB" shell mkdir -p "$STAGE"
"$ADB" push "$FIXTURE/." "$STAGE/" > "$OUT/fixture-push.txt"
"$ADB" shell run-as "$PACKAGE" sh -c "rm -rf '$ROOT_REL/versions/1.21.1' '$ROOT_REL/libraries' '$ROOT_REL/assets'; mkdir -p '$ROOT_REL'; cp -R '$STAGE/versions' '$ROOT_REL/'; cp -R '$STAGE/libraries' '$ROOT_REL/'; cp -R '$STAGE/assets' '$ROOT_REL/'"
"$ADB" shell rm -rf "$STAGE"

ASSET_INDEX_NAME="$(find "$FIXTURE/assets/indexes" -type f -name '*.json' -print -quit | xargs -r basename)"
test -n "$ASSET_INDEX_NAME"
"$ADB" shell run-as "$PACKAGE" sh -c "test -s '$ROOT_REL/versions/1.21.1/1.21.1.jar' && test -s '$ROOT_REL/versions/1.21.1/1.21.1.json' && find '$ROOT_REL/libraries' -type f | grep -q . && test -s '$ROOT_REL/assets/indexes/$ASSET_INDEX_NAME'" > "$OUT/staged-fixture-check.txt"

# Start the production launcher entry point, then follow its visible Play/Start control.
if ! "$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" > "$OUT/activity-start.txt" 2>&1; then
  "$ADB" shell monkey -p "$PACKAGE" 1 > "$OUT/monkey-start.txt" 2>&1
fi
sleep 8
"$ADB" shell uiautomator dump /sdcard/window.xml >/dev/null 2>&1 || true
"$ADB" shell cat /sdcard/window.xml > "$OUT/ui.xml" 2>/dev/null || true

PLAY_BOUNDS="$(grep -o 'text="\\(Play\\|Start\\)"[^>]*bounds="\\[[^\"]*\\]\\[[^\"]*\\]"' "$OUT/ui.xml" | head -n1 | sed -n 's/.*bounds="\\[\\([0-9]*\\),\\([0-9]*\\)\\]\\[\\([0-9]*\\),\\([0-9]*\\)\\]".*/\\1 \\2 \\3 \\4/p' || true)"
if [ -n "$PLAY_BOUNDS" ]; then
  read -r x1 y1 x2 y2 <<< "$PLAY_BOUNDS"
  "$ADB" shell input tap "$(( (x1+x2) / 2 ))" "$(( (y1+y2) / 2 ))" > "$OUT/play-tap.txt" 2>&1 || true
else
  echo 'No accessibility-visible Play/Start control found.' > "$OUT/play-tap.txt"
fi

for delay in 15 30 45 60; do
  sleep 15
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
done
"$ADB" shell dumpsys activity activities > "$OUT/activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/windows.txt" || true
cat "$OUT/logcat-60s.txt" > "$OUT/logcat.txt"
grep -Ei 'CraftDroid|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt"; then
  echo 'Step 182 detected a real Android/JVM/native launch failure.' >&2
  grep -Ei "$FATAL_RE" "$OUT/logcat.txt" >&2 || true
  exit 1
fi

if grep -Eiq 'MinecraftLaunchManager.*launch|NativeGameBridge.*launchJava|LaunchPreflight.*valid|Minecraft.*starting|Step [1-6]/6:' "$OUT/logcat.txt"; then
  echo 'Step 184 reached the production Minecraft launch path without fatal Android/JVM/native errors.' | tee "$OUT/result.txt"
else
  echo 'Step 184 staged real Minecraft 1.21.1 files but no concrete Minecraft JVM launch marker was observed.' | tee "$OUT/result.txt"
  exit 1
fi
