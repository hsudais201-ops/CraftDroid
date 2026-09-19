#!/usr/bin/env sh
set -eu
BASE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DIST_URL=$(sed -n 's/^distributionUrl=//p' "$BASE_DIR/gradle/wrapper/gradle-wrapper.properties" | sed 's#\\:#:#g' | sed 's#\\/#/#g')
DIST_URL=${DIST_URL:-https://services.gradle.org/distributions/gradle-9.6.0-bin.zip}
VERSION=$(printf '%s' "$DIST_URL" | sed -n 's#.*/gradle-\([^/]*\)-bin.zip#\1#p')
CACHE="${GRADLE_USER_HOME:-$HOME/.gradle}/craftdroid-wrapper/gradle-$VERSION"
if [ ! -x "$CACHE/bin/gradle" ]; then
  command -v curl >/dev/null 2>&1 || { echo "curl is required to bootstrap Gradle." >&2; exit 1; }
  TMP="${TMPDIR:-/tmp}/craftdroid-gradle-$$.zip"
  mkdir -p "$(dirname "$CACHE")"
  trap 'rm -f "$TMP"' EXIT INT TERM
  echo "Downloading Gradle $VERSION..." >&2
  curl -fL --retry 5 --retry-delay 2 --connect-timeout 20 --max-time 1800 "$DIST_URL" -o "$TMP"
  EXPECTED_SHA=$(sed -n 's/^distributionSha256Sum=//p' "$BASE_DIR/gradle/wrapper/gradle-wrapper.properties")
  if [ -n "$EXPECTED_SHA" ]; then
    command -v sha256sum >/dev/null 2>&1 || { echo "sha256sum is required when distributionSha256Sum is configured." >&2; exit 1; }
    ACTUAL_SHA=$(sha256sum "$TMP" | awk '{print $1}')
    if [ "$ACTUAL_SHA" != "$EXPECTED_SHA" ]; then
      echo "Gradle distribution checksum mismatch." >&2
      echo "Expected: $EXPECTED_SHA" >&2
      echo "Actual:   $ACTUAL_SHA" >&2
      exit 1
    fi
  fi
  rm -rf "$CACHE.tmp"
  mkdir -p "$CACHE.tmp"
  unzip -q "$TMP" -d "$CACHE.tmp"
  ROOT=$(find "$CACHE.tmp" -mindepth 1 -maxdepth 1 -type d | head -n 1)
  mv "$ROOT" "$CACHE"
  rm -rf "$CACHE.tmp"
fi
exec "$CACHE/bin/gradle" "$@"
