#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PATCHER="$ROOT/script/patch_steamclient_compat_gate.py"
DEFAULT_BACKUP="$HOME/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z/SteamRuntime.app/Contents/MacOS/steamclient.dylib"
DEFAULT_RUNTIME="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam/Contents/MacOS/steamclient.dylib"
if [ -f "$DEFAULT_BACKUP" ]; then
    DEFAULT_SOURCE="$DEFAULT_BACKUP"
else
    DEFAULT_SOURCE="$DEFAULT_RUNTIME"
fi
SOURCE="${STEAMCLIENT_PATH:-$DEFAULT_SOURCE}"
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

test -x "$PATCHER"
test -f "$SOURCE"

SOURCE_HASH=$(shasum -a 256 "$SOURCE" | awk '{print $1}')
OUTPUT="$TMP_ROOT/steamclient.dylib"

"$PATCHER" --input "$SOURCE" --output "$OUTPUT"
"$PATCHER" --verify-patched "$OUTPUT"

test "$(shasum -a 256 "$SOURCE" | awk '{print $1}')" = "$SOURCE_HASH"
test "$(shasum -a 256 "$OUTPUT" | awk '{print $1}')" != "$SOURCE_HASH"

if "$PATCHER" --input "$OUTPUT" --output "$TMP_ROOT/twice.dylib" >/dev/null 2>&1; then
    echo "patcher must refuse an already-patched input" >&2
    exit 1
fi

echo "steamclient compatibility gate patch: PASS"
