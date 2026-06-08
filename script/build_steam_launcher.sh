#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/launcher/steam_launcher.c"
OUTPUT_DIR="$ROOT/artifacts/steam-launcher"
OUTPUT="$OUTPUT_DIR/realsteamonmac_launcher"

mkdir -p "$OUTPUT_DIR"

xcrun clang \
    -arch arm64 \
    -arch x86_64 \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$OUTPUT" \
    "$SOURCE"

codesign --force --sign - "$OUTPUT"
echo "$OUTPUT"
