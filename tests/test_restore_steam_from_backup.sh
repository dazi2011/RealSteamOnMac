#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

STEAM_APP="$TMP_ROOT/Steam.app"
RUNTIME_APP="$TMP_ROOT/SteamRuntime.app"
SUPPORT="$TMP_ROOT/support"
BACKUP="$TMP_ROOT/backup"
HOLD="$TMP_ROOT/hold"

mkdir -p \
    "$STEAM_APP/Contents/MacOS" \
    "$RUNTIME_APP/Contents/MacOS" \
    "$SUPPORT" \
    "$BACKUP/Steam.app/Contents/MacOS" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS"

printf 'modified app\n' >"$STEAM_APP/Contents/MacOS/marker"
printf 'modified runtime\n' >"$RUNTIME_APP/Contents/MacOS/steam_osx"
printf 'modified steamclient\n' >"$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
printf 'support\n' >"$SUPPORT/marker"
printf 'clean app\n' >"$BACKUP/Steam.app/Contents/MacOS/marker"
printf 'clean runtime\n' >"$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"
printf 'clean steamclient\n' \
    >"$BACKUP/SteamRuntime.app/Contents/MacOS/steamclient.dylib"
chmod +x \
    "$RUNTIME_APP/Contents/MacOS/steam_osx" \
    "$BACKUP/SteamRuntime.app/Contents/MacOS/steam_osx"

"$ROOT/script/restore_steam_from_backup.sh" \
    --clean-backup "$BACKUP" \
    --steam-app "$STEAM_APP" \
    --runtime-app "$RUNTIME_APP" \
    --support-root "$SUPPORT" \
    --hold-root "$HOLD" >/dev/null

grep -q 'clean app' "$STEAM_APP/Contents/MacOS/marker"
grep -q 'clean runtime' "$RUNTIME_APP/Contents/MacOS/steam_osx"
grep -q 'clean steamclient' "$RUNTIME_APP/Contents/MacOS/steamclient.dylib"
test ! -e "$SUPPORT"
test "$(find "$HOLD" -name 'Steam.app.modified' -type d | wc -l)" -eq 1
test "$(find "$HOLD" -name 'RealSteamOnMac-support.disabled' -type d | wc -l)" -eq 1

echo "Steam restore contract: PASS"
