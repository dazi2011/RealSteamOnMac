#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP_ROOT=$(mktemp -d)
trap 'rm -rf "$TMP_ROOT"' EXIT

REALSTEAMONMAC_CONFIG_ROOT="$TMP_ROOT/config" \
    "$ROOT/script/install_runtime_config.sh"

CONFIG="$TMP_ROOT/config/allowlist.txt"
test -f "$CONFIG"
grep -q '^1118200$' "$CONFIG"
if grep -Eq '^[[:space:]]*0[[:space:]]*$' "$CONFIG"; then
    echo "allowlist must not contain the global AppID" >&2
    exit 1
fi

echo "runtime allowlist contract: PASS"
