#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROBE="$ROOT/probes/library_native_actions_readonly.js"

node --check "$PROBE"
grep -q 'SteamUIStore?.WindowStore' "$PROBE"
grep -q 'm_rgWindows' "$PROBE"
grep -q 'pointerEvents' "$PROBE"
grep -q 'sizeOnDisk' "$PROBE"

if grep -Eq '\.click\(|\.OnClick\(' "$PROBE"; then
  printf '%s\n' "read-only action probe must not invoke Steam actions" >&2
  exit 1
fi
