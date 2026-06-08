#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
SET_PROBE="$ROOT/probes/set_global_compat_experimental.js"
CLEAR_PROBE="$ROOT/probes/clear_global_compat_experimental.js"

test -f "$SET_PROBE"
test -f "$CLEAR_PROBE"
grep -q 'const toolName = "realsteamonmac-experimental";' "$SET_PROBE"
grep -q 'SpecifyGlobalCompatTool(toolName)' "$SET_PROBE"
grep -q 'SpecifyGlobalCompatTool("")' "$CLEAR_PROBE"

echo "global compatibility probe contract: PASS"
