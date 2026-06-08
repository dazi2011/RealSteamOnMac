#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/hook/compat_gate_hook.c"
OUTPUT_DIR="$ROOT/artifacts/compat-gate-hook"
OUTPUT="$OUTPUT_DIR/libRealSteamCompatGate.dylib"

mkdir -p "$OUTPUT_DIR"

xcrun clang \
    -arch arm64 \
    -arch arm64e \
    -arch x86_64 \
    -dynamiclib \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$OUTPUT" \
    "$SOURCE"

codesign --force --sign - "$OUTPUT"
echo "$OUTPUT"
