#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PATCHER="$ROOT/script/patch_steamclient_compat_gate.py"
DEFAULT_BACKUP="$HOME/RealSteamOnMac-Backups/steam-1780705203-20260607T083704Z/SteamRuntime.app/Contents/MacOS/steamclient.dylib"
DEFAULT_RUNTIME="$HOME/Library/Application Support/Steam/Steam.AppBundle/Steam/Contents/MacOS/steamclient.dylib"
CURRENT_REFRESH_HASH=234a51d3ed72fadffc88b5dd3d176b372475fc0eb49442d3936802180c574cb6
if [ -f "$DEFAULT_RUNTIME" ] &&
    [ "$(shasum -a 256 "$DEFAULT_RUNTIME" | awk '{print $1}')" = "$CURRENT_REFRESH_HASH" ]; then
    DEFAULT_SOURCE="$DEFAULT_RUNTIME"
elif [ -f "$DEFAULT_BACKUP" ]; then
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
case "$SOURCE_HASH" in
    f9c1df763087900a66020635f22559f49533edd3290f0880eb13f46d2dfe2ed5)
        EXPECTED_BUILD=1780705203
        ;;
    d0945fc67880d048d163cf071ec9cc264cb3618c56cfb73520da36de0188f13e)
        EXPECTED_BUILD=1780965181
        ;;
    15c231465c4df4f557ece6aba070e7601e00b2b17b3772d2248655d41dbbeae2)
        EXPECTED_BUILD=1780965181
        ;;
    234a51d3ed72fadffc88b5dd3d176b372475fc0eb49442d3936802180c574cb6)
        EXPECTED_BUILD=1781212412
        ;;
    *)
        echo "test source is not a supported Steam build" >&2
        exit 1
        ;;
esac
OUTPUT="$TMP_ROOT/steamclient.dylib"

"$PATCHER" --input "$SOURCE" --output "$OUTPUT" \
    >"$TMP_ROOT/patch.log"
cat "$TMP_ROOT/patch.log"
"$PATCHER" --verify-patched "$OUTPUT" \
    >"$TMP_ROOT/verify.log"
cat "$TMP_ROOT/verify.log"
grep -q "steam_build=$EXPECTED_BUILD" "$TMP_ROOT/patch.log"
grep -q "steam_build=$EXPECTED_BUILD" "$TMP_ROOT/verify.log"

test "$(shasum -a 256 "$SOURCE" | awk '{print $1}')" = "$SOURCE_HASH"
test "$(shasum -a 256 "$OUTPUT" | awk '{print $1}')" != "$SOURCE_HASH"

if "$PATCHER" --input "$OUTPUT" --output "$TMP_ROOT/twice.dylib" >/dev/null 2>&1; then
    echo "patcher must refuse an already-patched input" >&2
    exit 1
fi

echo "steamclient compatibility gate patch: PASS"
