#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
HOOK="$ROOT/artifacts/compat-gate-hook/libRealSteamCompatGate.dylib"
ENGINE="$ROOT/artifacts/compat-gate-hook/libRealSteamNativeEngine.dylib"
HOOK_SOURCE="$ROOT/hook/injection_guard.c"
ENGINE_SOURCE="$ROOT/hook/compat_gate_hook.c"
HARNESS_SOURCE="$ROOT/tests/fixtures/hook_environment_harness.c"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

CONSTRUCTOR=$(
  sed -n \
    '/initialize_injection_guard(void)/,/^}/p' \
    "$HOOK_SOURCE"
)
if printf '%s\n' "$CONSTRUCTOR" |
   grep -Eq \
     'pthread_create|data_override_worker|is_steam_runtime_process|log_line|get_executable_path'; then
  echo "hook constructor must only clear inherited injection variables" >&2
  exit 1
fi

"$ROOT/script/build_compat_gate_hook.sh" >/dev/null

for forbidden in pthread_create pthread_detach usleep __NSGetExecutablePath; do
  if nm -u "$HOOK" | grep -Fq "$forbidden"; then
    echo "startup injection guard imports forbidden symbol: $forbidden" >&2
    exit 1
  fi
done
if grep -q '__attribute__((constructor))' "$ENGINE_SOURCE"; then
  echo "native engine must not contain a dyld constructor" >&2
  exit 1
fi
test -f "$ENGINE"

RUNTIME_DIR="$TMP/Steam.AppBundle/Steam/Contents/MacOS"
RUNTIME="$RUNTIME_DIR/steam_osx"
mkdir -p "$RUNTIME_DIR" "$TMP/home"
xcrun clang \
  -Wall \
  -Wextra \
  -Werror \
  -o "$RUNTIME" \
  "$HARNESS_SOURCE"

HOME="$TMP/home" "$RUNTIME" "$HOOK"

echo "hook environment isolation: PASS"
