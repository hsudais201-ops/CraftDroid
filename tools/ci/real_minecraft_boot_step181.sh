#!/usr/bin/env bash
set -euo pipefail

APK="${1:?usage: real_minecraft_boot_step181.sh <apk> <output-dir>}"
OUT="${2:?usage: real_minecraft_boot_step181.sh <apk> <output-dir>}"
mkdir -p "$OUT"
ADB="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/platform-tools/adb"
AAPT="${ANDROID_HOME:-$ANDROID_SDK_ROOT}/build-tools/36.0.0/aapt"

PACKAGE="$($AAPT dump badging "$APK" | sed -n "s/^package: name='\([^']*\)'.*/\1/p" | head -n1)"
ACTIVITY="$($AAPT dump badging "$APK" | sed -n "s/^launchable-activity: name='\([^']*\)'.*/\1/p" | head -n1)"
test -n "$PACKAGE" && test -n "$ACTIVITY"
printf '%s\n' "$PACKAGE" > "$OUT/package.txt"
printf '%s\n' "$ACTIVITY" > "$OUT/activity.txt"

"$ADB" wait-for-device
"$ADB" install -r "$APK"
"$ADB" shell am force-stop "$PACKAGE" || true
"$ADB" logcat -c

# Start the real launcher entry point. Do not fake a Minecraft boot by invoking
# a host-side JVM; this test only records what the Android launcher actually does.
if ! "$ADB" shell am start -W -n "$PACKAGE/$ACTIVITY" > "$OUT/activity-start.txt" 2>&1; then
  "$ADB" shell monkey -p "$PACKAGE" 1 > "$OUT/monkey-start.txt" 2>&1
fi

# Give the application time to initialize its game/runtime path, then capture
# both application markers and native/JVM failures.
for delay in 5 15 30 45; do
  sleep $((delay == 5 ? 5 : delay - 15))
  "$ADB" logcat -d -v threadtime > "$OUT/logcat-${delay}s.txt"
done
"$ADB" shell dumpsys activity activities > "$OUT/activities.txt" || true
"$ADB" shell dumpsys window windows > "$OUT/windows.txt" || true

cat "$OUT/logcat-45s.txt" > "$OUT/logcat.txt"
grep -Ei 'CraftDroid|MinecraftLaunchManager|LaunchPreflight|NativeGameBridge|JavaRuntime|Renderer|GLFW|LWJGL|Minecraft|SIG|FATAL|Exception|Error|dlopen|CANNOT LINK|OutOfMemory' "$OUT/logcat.txt" > "$OUT/filtered-launch-log.txt" || true

FATAL_RE='FATAL EXCEPTION|Fatal signal|SIGSEGV|SIGABRT|SIGBUS|SIGILL|UnsatisfiedLinkError|NoClassDefFoundError|ClassNotFoundException|ExceptionInInitializerError|dlopen failed|CANNOT LINK|OutOfMemoryError|GLFW.*(error|failed)|LWJGL.*(error|failed)'
if grep -Eiq "$FATAL_RE" "$OUT/logcat.txt"; then
  echo 'Step 181 detected a real Android/JVM/native launch failure.' >&2
  grep -Ei "$FATAL_RE" "$OUT/logcat.txt" >&2 || true
  exit 1
fi

# A running launcher is not itself proof of Minecraft boot. Require a concrete
# launch marker from the production path before calling this a Minecraft launch.
if grep -Eiq 'NativeGameBridge.*launchJava|MinecraftLaunchManager.*launch|Minecraft.*starting|LaunchPreflight.*valid' "$OUT/logcat.txt"; then
  echo 'Step 181 launch marker detected.' | tee "$OUT/result.txt"
else
  echo 'Step 181 did not reach a concrete Minecraft JVM launch marker; launcher startup remained healthy but game boot was not proven.' | tee "$OUT/result.txt"
fi
