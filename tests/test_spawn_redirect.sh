#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SOURCE="$ROOT/hook/compat_gate_hook.c"
HARNESS_SOURCE="$ROOT/tests/fixtures/spawn_redirect_harness.c"
TEMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TEMP_ROOT"' EXIT
TEST_ENGINE="$TEMP_ROOT/libRealSteamNativeEngineTest.dylib"

grep -q 'managed-registry-v1.txt' "$SOURCE"
grep -q 'realsteamonmac_should_redirect_spawn' "$SOURCE"
grep -q 'validate_shortcut_target' "$SOURCE"
grep -q 'shortcut_file_identity_matches' "$SOURCE"
grep -q -- '--shortcut-id' "$SOURCE"
grep -q 'is_missing_launch_target' "$SOURCE"
grep -q 'has_app_suffix' "$SOURCE"
grep -q 'spawn_appid' "$SOURCE"
grep -q '/usr/bin/python3' "$SOURCE"
grep -Fq 'redirected[1] = "-I"' "$SOURCE"
grep -q 'build_redirect_environment' "$SOURCE"
grep -q 'realsteamonmac-runtime' "$SOURCE"

xcrun clang \
    -DREALSTEAMONMAC_TESTING=1 \
    -dynamiclib \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$TEST_ENGINE" \
    "$SOURCE"

xcrun clang \
    -Wall \
    -Wextra \
    -Werror \
    -Os \
    -o "$TEMP_ROOT/spawn-redirect-harness" \
    "$HARNESS_SOURCE"

"$TEMP_ROOT/spawn-redirect-harness" "$TEST_ENGINE"

echo "spawn redirect: PASS"
