#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/hook/compat_gate_hook.c"
BUILD_SCRIPT="$ROOT/script/build_compat_gate_hook.sh"
ENGINE="$ROOT/artifacts/compat-gate-hook/libRealSteamNativeEngine.dylib"
HARNESS_SOURCE="$ROOT/tests/fixtures/spawn_redirect_harness.c"
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT

grep -q 'STEAMCLIENT_POSIX_SPAWN_POINTER_OFFSET' "$SOURCE"
grep -q '0x018F9500' "$SOURCE"
grep -q '0x01945548' "$SOURCE"
grep -q 'realsteamonmac_should_redirect_spawn' "$SOURCE"
grep -q 'is_pe_executable' "$SOURCE"
grep -q 'is_missing_launch_target' "$SOURCE"
grep -q 'has_app_suffix' "$SOURCE"
grep -q 'spawn_appid' "$SOURCE"
grep -q 'is_allowlisted(appid)' "$SOURCE"
grep -q '/usr/bin/python3' "$SOURCE"
grep -q 'realsteamonmac-runtime' "$SOURCE"
grep -q 'spawn: installed allowlist-scoped launch redirect' "$SOURCE"

"$BUILD_SCRIPT" >/dev/null
xcrun clang \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$TEMP_ROOT/spawn-redirect-harness" \
    "$HARNESS_SOURCE"

"$TEMP_ROOT/spawn-redirect-harness" "$ENGINE"

echo "spawn redirect: PASS"
