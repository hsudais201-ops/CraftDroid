#!/usr/bin/env bash
set -euo pipefail
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

test -x ./gradlew
test -f gradle/wrapper/gradle-wrapper.properties
test -f .github/workflows/build-apk.yml

grep -q '^distributionUrl=.*gradle-9\.6\.0-bin\.zip' gradle/wrapper/gradle-wrapper.properties
grep -q '^distributionSha256Sum=' gradle/wrapper/gradle-wrapper.properties

grep -q 'uses: gradle/actions/setup-gradle@v6' .github/workflows/build-apk.yml
grep -q 'uses: android-actions/setup-android@v3' .github/workflows/build-apk.yml
grep -q 'uses: reactivecircus/android-emulator-runner@v2' .github/workflows/build-apk.yml
grep -q 'run: gradle --no-daemon --stacktrace :app:assembleDebug' .github/workflows/build-apk.yml

echo 'CraftDroid CI project verification: PASS'
