#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
BUILD_SCRIPT="$ROOT/script/build_compat_gate_hook.sh"
ENGINE="$ROOT/artifacts/compat-gate-hook/libRealSteamNativeEngine.dylib"
HARNESS_SOURCE="$ROOT/tests/fixtures/native_registry_server_harness.c"
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT

"$BUILD_SCRIPT" >/dev/null

xcrun clang \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$TEMP_ROOT/native-registry-server-harness" \
    "$HARNESS_SOURCE"

"$TEMP_ROOT/native-registry-server-harness" "$ENGINE"

echo "native registry server: PASS"
