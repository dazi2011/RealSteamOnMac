#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
PROBE="$ROOT/probes/specify_people_playground.js"

test -f "$PROBE"
grep -q 'const appid = 1118200;' "$PROBE"
grep -q 'const toolName = "realsteamonmac-experimental";' "$PROBE"

if grep -Eq 'SpecifyCompatTool\([[:space:]]*[0-9]' "$PROBE"; then
    echo "SpecifyCompatTool must use the guarded appid variable" >&2
    exit 1
fi

echo "specify probe safety contract: PASS"
