#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
GUARD_SOURCE="$ROOT/hook/injection_guard.c"
ENGINE_SOURCE="$ROOT/hook/compat_gate_hook.c"
OUTPUT_DIR="$ROOT/artifacts/compat-gate-hook"
GUARD_OUTPUT="$OUTPUT_DIR/libRealSteamCompatGate.dylib"
ENGINE_OUTPUT="$OUTPUT_DIR/libRealSteamNativeEngine.dylib"

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
    -o "$GUARD_OUTPUT" \
    "$GUARD_SOURCE"

xcrun clang \
    -arch arm64 \
    -arch arm64e \
    -arch x86_64 \
    -dynamiclib \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$ENGINE_OUTPUT" \
    "$ENGINE_SOURCE"

codesign --force --sign - "$GUARD_OUTPUT"
codesign --force --sign - "$ENGINE_OUTPUT"
printf '%s\n' "$GUARD_OUTPUT" "$ENGINE_OUTPUT"
