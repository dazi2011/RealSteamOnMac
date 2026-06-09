#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SOURCE="$ROOT/probes/close_windows_by_title.c"
BUILD_DIR=$(mktemp -d)
trap 'rm -rf "$BUILD_DIR"' EXIT

x86_64-w64-mingw32-gcc \
    -O2 \
    -s \
    -static \
    -Wall \
    -Wextra \
    -Werror \
    -o "$BUILD_DIR/close-window.exe" \
    "$SOURCE"

test -s "$BUILD_DIR/close-window.exe"
file "$BUILD_DIR/close-window.exe" | grep -q 'PE32+ executable'
strings "$BUILD_DIR/close-window.exe" | grep -q 'WM_CLOSE'
strings "$BUILD_DIR/close-window.exe" | grep -q 'no matching window found'

echo "close-window probe contract: PASS"
